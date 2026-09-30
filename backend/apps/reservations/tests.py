import json
import threading
from datetime import time, timedelta
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from openpyxl import load_workbook
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from unittest.mock import patch

from apps.common.factories import make_room, make_user
from apps.common.utils import aware_on
from apps.facecore.errors import FaceError
from apps.reservations.models import CheckIn, Reservation
from apps.rooms.models import RoomSlot
from apps.users.models import FaceProfile, User


def auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


def tomorrow():
    return timezone.localdate() + timedelta(days=1)


def jpeg_file():
    from PIL import Image

    buffer = BytesIO()
    Image.new('RGB', (64, 64), (210, 170, 130)).save(buffer, format='JPEG')
    return SimpleUploadedFile('face.jpg', buffer.getvalue(), content_type='image/jpeg')


def book(client, seat, slot, day):
    return client.post('/api/v1/reservations/', {
        'seat_id': seat.id,
        'slot_id': slot.id,
        'reserve_date': day.isoformat(),
    }, format='json')


VECTOR = [1.0] + [0.0] * 511


class AuthTests(TestCase):
    def test_register_login_and_profile(self):
        client = APIClient()
        created = client.post('/api/v1/auth/register/', {
            'username': 'stu001',
            'password': 'password123',
            'nickname': '小周',
            'phone': '13900139000',
            'student_no': '2024999',
            'role': 'admin',
        }, format='json')
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.data['code'], 0)
        self.assertEqual(User.objects.get(username='stu001').role, 'student')

        logged = client.post('/api/v1/auth/login/', {
            'username': 'stu001',
            'password': 'wrong-password',
        }, format='json')
        self.assertEqual(logged.status_code, 401)

        logged = client.post('/api/v1/auth/login/', {
            'username': 'stu001',
            'password': 'password123',
        }, format='json')
        self.assertEqual(logged.status_code, 200)
        self.assertEqual(logged.data['data']['role'], 'student')
        access = logged.data['data']['access']

        client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        renamed = client.patch('/api/v1/users/me/', {'nickname': '周周', 'phone': '13900139001'}, format='json')
        self.assertEqual(renamed.status_code, 200)
        self.assertEqual(renamed.data['data']['nickname'], '周周')
        self.assertEqual(renamed.data['data']['role'], 'student')

        forbidden = client.get('/api/v1/stats/overview/')
        self.assertEqual(forbidden.status_code, 403)

    def test_disabled_account_gets_403(self):
        user = make_user('frozen')
        user.is_active = False
        user.save(update_fields=['is_active'])
        response = APIClient().post('/api/v1/auth/login/', {
            'username': 'frozen',
            'password': 'password123',
        }, format='json')
        self.assertEqual(response.status_code, 403)

    def test_admin_can_open_overview(self):
        admin = make_user('root', role='admin')
        response = auth_client(admin).get('/api/v1/stats/overview/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['code'], 0)
        self.assertIn('open_rooms', response.data['data'])


class BookingTests(TestCase):
    def setUp(self):
        self.student = make_user('ming')
        self.other = make_user('hong', student_no='hong001')
        self.admin = make_user('manager', role='admin')
        self.room, self.slot = make_room('开放室')
        self.seat = self.room.seats.get(code='A-01')
        self.other_seat = self.room.seats.get(code='A-02')
        self.day = tomorrow()
        self.student_client = auth_client(self.student)
        self.other_client = auth_client(self.other)
        self.admin_client = auth_client(self.admin)

    def test_maintenance_room_cannot_be_booked(self):
        closed, slot = make_room('维护室', status='maintenance')
        response = book(self.student_client, closed.seats.first(), slot, self.day)
        self.assertEqual(response.status_code, 400)
        self.assertIn('不可预约', response.data['message'])

    def test_seat_colors_and_owner_visibility(self):
        created = book(self.student_client, self.seat, self.slot, self.day)
        self.assertEqual(created.status_code, 200)
        params = {'date': self.day.isoformat(), 'slot_id': self.slot.id}
        others = self.other_client.get(f'/api/v1/rooms/{self.room.id}/seats/', params)
        taken = next(item for item in others.data['data']['seats'] if item['code'] == 'A-01')
        free = next(item for item in others.data['data']['seats'] if item['code'] == 'A-02')
        self.assertEqual(taken['status'], 'reserved')
        self.assertEqual(taken['color'], '#f59e0b')
        self.assertIsNone(taken['reservation_id'])
        self.assertEqual(free['status'], 'free')
        self.assertEqual(free['color'], '#22c55e')
        self.assertTrue(free['can_book'])

        mine = self.student_client.get(f'/api/v1/rooms/{self.room.id}/seats/', params)
        own = next(item for item in mine.data['data']['seats'] if item['code'] == 'A-01')
        self.assertEqual(own['reservation_id'], created.data['data']['id'])

    def test_overlap_and_cancel_then_rebook(self):
        RoomSlot.objects.create(
            room=self.room,
            name='重叠',
            start_time=time(15, 0),
            end_time=time(17, 0),
            enabled=True,
            sort_order=2,
        )
        overlap = self.room.slots.get(name='重叠')
        first = book(self.student_client, self.seat, self.slot, self.day)
        self.assertEqual(first.status_code, 200)
        second = book(self.student_client, self.other_seat, overlap, self.day)
        self.assertEqual(second.status_code, 400)

        cancelled = self.student_client.post(f"/api/v1/reservations/{first.data['data']['id']}/cancel/")
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.data['data']['status'], 'cancelled')
        again = book(self.other_client, self.seat, self.slot, self.day)
        self.assertEqual(again.status_code, 200)

    def test_cannot_cancel_after_start(self):
        created = book(self.student_client, self.seat, self.slot, self.day)
        reservation = Reservation.objects.get(pk=created.data['data']['id'])
        reservation.start_at = timezone.now() - timedelta(minutes=5)
        reservation.save(update_fields=['start_at', 'updated_at'])
        response = self.student_client.post(f'/api/v1/reservations/{reservation.id}/cancel/')
        self.assertEqual(response.status_code, 400)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'pending')

    def test_close_room_cancels_future_and_blocks_new_booking(self):
        created = book(self.student_client, self.seat, self.slot, self.day)
        response = self.admin_client.patch(f'/api/v1/rooms/{self.room.id}/', {'status': 'maintenance'}, format='json')
        self.assertEqual(response.status_code, 200)
        reservation = Reservation.objects.get(pk=created.data['data']['id'])
        self.assertEqual(reservation.status, 'admin_cancelled')
        self.assertEqual(reservation.cancel_reason, '自习室维护')
        hidden = self.student_client.get('/api/v1/rooms/')
        self.assertFalse(any(item['id'] == self.room.id for item in hidden.data['data']))
        denied = book(self.other_client, self.other_seat, self.slot, self.day)
        self.assertEqual(denied.status_code, 400)

    def test_disable_seat_keeps_history(self):
        created = book(self.student_client, self.seat, self.slot, self.day)
        response = self.admin_client.patch(f'/api/v1/seats/{self.seat.id}/', {'enabled': False}, format='json')
        self.assertEqual(response.status_code, 200)
        params = {'date': self.day.isoformat(), 'slot_id': self.slot.id}
        board = self.student_client.get(f'/api/v1/rooms/{self.room.id}/seats/', params)
        target = next(item for item in board.data['data']['seats'] if item['id'] == self.seat.id)
        self.assertEqual(target['status'], 'unavailable')
        self.assertEqual(target['color'], '#9ca3af')
        records = self.student_client.get('/api/v1/reservations/mine/')
        row = next(item for item in records.data['data']['results'] if item['id'] == created.data['data']['id'])
        self.assertEqual(row['status'], 'admin_cancelled')

    def test_filter_and_export(self):
        created = book(self.student_client, self.seat, self.slot, self.day)
        self.assertEqual(created.status_code, 200)
        other_day = self.day + timedelta(days=1)
        Reservation.objects.create(
            user=self.student,
            room=self.room,
            seat=self.other_seat,
            slot=self.slot,
            reserve_date=other_day,
            start_at=aware_on(other_day, self.slot.start_time),
            end_at=aware_on(other_day, self.slot.end_time),
            status='pending',
        )
        params = {'date_from': self.day.isoformat(), 'date_to': self.day.isoformat()}
        listed = self.student_client.get('/api/v1/reservations/mine/', params)
        self.assertEqual(listed.data['data']['count'], 1)
        exported = self.student_client.get('/api/v1/reservations/mine/export/', params)
        self.assertEqual(exported.status_code, 200)
        self.assertIn('spreadsheetml', exported['Content-Type'])
        sheet = load_workbook(BytesIO(exported.content)).active
        self.assertEqual(sheet.max_row, 2)
        self.assertEqual(sheet.cell(2, 4).value, 'A-01')


class FaceAndSweepTests(TestCase):
    def setUp(self):
        self.student = make_user('face-user')
        self.room, self.slot = make_room('签到室')
        self.seat = self.room.seats.get(code='A-01')
        self.day = tomorrow()
        self.client = auth_client(self.student)
        created = book(self.client, self.seat, self.slot, self.day)
        self.reservation = Reservation.objects.get(pk=created.data['data']['id'])

    def _open_window(self):
        self.reservation.start_at = timezone.now() - timedelta(minutes=5)
        self.reservation.save(update_fields=['start_at', 'updated_at'])

    def test_checkin_outside_window(self):
        self.reservation.start_at = timezone.now() - timedelta(minutes=30)
        self.reservation.save(update_fields=['start_at', 'updated_at'])
        response = self.client.post(
            f'/api/v1/reservations/{self.reservation.id}/check-in/',
            {'image': jpeg_file()},
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('窗口', response.data['message'])
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, 'pending')
        self.assertTrue(CheckIn.objects.filter(reservation=self.reservation, result='reject').exists())

    def test_checkin_requires_enrollment(self):
        self._open_window()
        response = self.client.post(
            f'/api/v1/reservations/{self.reservation.id}/check-in/',
            {'image': jpeg_file()},
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('采集', response.data['message'])
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, 'pending')

    @patch('apps.facecore.service.compare', return_value=0.9)
    @patch('apps.facecore.service.extract_embedding', return_value=VECTOR)
    def test_owner_face_checks_in_and_turns_seat_red(self, _extract, _compare):
        FaceProfile.objects.create(user=self.student, embedding=json.dumps(VECTOR))
        self.student.face_enrolled = True
        self.student.save(update_fields=['face_enrolled'])
        self._open_window()
        response = self.client.post(
            f'/api/v1/reservations/{self.reservation.id}/check-in/',
            {'image': jpeg_file()},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['data']['passed'])
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, 'checked_in')
        params = {'date': self.day.isoformat(), 'slot_id': self.slot.id}
        board = self.client.get(f'/api/v1/rooms/{self.room.id}/seats/', params)
        seat = next(item for item in board.data['data']['seats'] if item['id'] == self.seat.id)
        self.assertEqual(seat['status'], 'occupied')
        self.assertEqual(seat['color'], '#ef4444')

    @patch('apps.facecore.service.compare', return_value=0.1)
    @patch('apps.facecore.service.extract_embedding', return_value=VECTOR)
    def test_other_face_is_rejected(self, _extract, _compare):
        FaceProfile.objects.create(user=self.student, embedding=json.dumps(VECTOR))
        self.student.face_enrolled = True
        self.student.save(update_fields=['face_enrolled'])
        self._open_window()
        response = self.client.post(
            f'/api/v1/reservations/{self.reservation.id}/check-in/',
            {'image': jpeg_file()},
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('未通过', response.data['message'])
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, 'pending')

    @patch('apps.users.views.extract_embedding', side_effect=FaceError('multiple_faces'))
    def test_enroll_rejects_multiple_faces(self, _extract):
        response = self.client.post('/api/v1/face/enroll/', {'image': jpeg_file()}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.student.refresh_from_db()
        self.assertFalse(self.student.face_enrolled)

    @patch('apps.users.views.extract_embedding', return_value=VECTOR)
    def test_enroll_saves_profile(self, _extract):
        response = self.client.post('/api/v1/face/enroll/', {'image': jpeg_file()}, format='multipart')
        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertTrue(self.student.face_enrolled)
        self.assertEqual(len(self.student.face_profile.vector()), 512)

    def test_sweep_expires_and_completes(self):
        self.reservation.start_at = timezone.now() - timedelta(hours=3)
        self.reservation.end_at = timezone.now() - timedelta(hours=1)
        self.reservation.save(update_fields=['start_at', 'end_at', 'updated_at'])
        finished = Reservation.objects.create(
            user=self.student,
            room=self.room,
            seat=self.room.seats.get(code='A-02'),
            slot=self.slot,
            reserve_date=self.day,
            start_at=timezone.now() - timedelta(hours=3),
            end_at=timezone.now() - timedelta(minutes=1),
            status='checked_in',
        )
        call_command('sweep_reservations')
        self.reservation.refresh_from_db()
        finished.refresh_from_db()
        self.assertEqual(self.reservation.status, 'expired')
        self.assertEqual(finished.status, 'completed')


class StatsTests(TestCase):
    def test_utilization_and_activity(self):
        admin = make_user('stat-admin', role='admin')
        room, slot = make_room('统计室', seats=4)
        day = tomorrow()
        seats = list(room.seats.order_by('code'))
        student = make_user('active-user', student_no='A100')
        for seat in seats[:2]:
            Reservation.objects.create(
                user=student,
                room=room,
                seat=seat,
                slot=slot,
                reserve_date=day,
                start_at=aware_on(day, slot.start_time),
                end_at=aware_on(day, slot.end_time),
                status='checked_in',
            )
        activity_room, activity_slot = make_room('活动室', seats=4)
        activity_seats = list(activity_room.seats.order_by('code'))
        high = make_user('high-user', student_no='A200')
        low = make_user('low-user', student_no='A300')
        normal = make_user('normal-user', student_no='A400')
        quiet = make_user('quiet-user', student_no='A500')
        for _ in range(8):
            Reservation.objects.create(
                user=high, room=activity_room, seat=activity_seats[0], slot=activity_slot, reserve_date=day,
                start_at=aware_on(day, activity_slot.start_time), end_at=aware_on(day, activity_slot.end_time),
                status='completed',
            )
        for _ in range(3):
            Reservation.objects.create(
                user=low, room=activity_room, seat=activity_seats[1], slot=activity_slot, reserve_date=day,
                start_at=aware_on(day, activity_slot.start_time), end_at=aware_on(day, activity_slot.end_time),
                status='expired',
            )
        for _ in range(3):
            Reservation.objects.create(
                user=normal, room=activity_room, seat=activity_seats[2], slot=activity_slot, reserve_date=day,
                start_at=aware_on(day, activity_slot.start_time), end_at=aware_on(day, activity_slot.end_time),
                status='completed',
            )
        client = auth_client(admin)
        params = {'date_from': day.isoformat(), 'date_to': day.isoformat()}
        usage = client.get('/api/v1/stats/utilization/', params)
        self.assertEqual(usage.status_code, 200)
        room_row = next(item for item in usage.data['data']['rooms'] if item['room_id'] == room.id)
        self.assertAlmostEqual(room_row['usage_rate'], 0.5)
        self.assertAlmostEqual(room_row['reservation_rate'], 0.5)

        seats_stats = client.get('/api/v1/stats/seats/', params)
        by_code = {item['code']: item for item in seats_stats.data['data']['items'] if item['room_id'] == room.id}
        self.assertEqual(by_code['A-01']['occupied_minutes'], 120)
        self.assertEqual(by_code['A-03']['free_minutes'], 120)
        self.assertEqual(by_code['A-03']['occupied_minutes'], 0)

        people = {item['username']: item for item in client.get('/api/v1/stats/users/', params).data['data']['items']}
        self.assertEqual(people['high-user']['label'], '高活跃')
        self.assertEqual(people['low-user']['label'], '低活跃')
        self.assertEqual(people['normal-user']['label'], '普通')
        self.assertEqual(people['quiet-user']['label'], '样本不足')
        self.assertIsNone(people['quiet-user']['checkin_rate'])


class ConcurrencyTests(TransactionTestCase):
    def test_only_one_booking_wins(self):
        first = make_user('race1', student_no='R001')
        second = make_user('race2', student_no='R002')
        room, slot = make_room('抢座室')
        seat = room.seats.get(code='A-01')
        day = tomorrow().isoformat()
        tokens = [str(RefreshToken.for_user(user).access_token) for user in (first, second)]
        from django.db import connections
        connections.close_all()
        barrier = threading.Barrier(2)
        results = []
        errors = []

        def hit(token):
            from django.db import connections

            try:
                connections.close_all()
                barrier.wait(timeout=10)
                client = APIClient()
                client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
                response = client.post('/api/v1/reservations/', {
                    'seat_id': seat.id,
                    'slot_id': slot.id,
                    'reserve_date': day,
                }, format='json')
                results.append(response.status_code)
            except Exception as exc:
                errors.append(exc)
            finally:
                connections.close_all()

        threads = [threading.Thread(target=hit, args=(token,)) for token in tokens]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)
        self.assertFalse(errors, errors)
        self.assertCountEqual(results, [200, 409])
        self.assertEqual(Reservation.objects.filter(seat=seat, status='pending').count(), 1)
