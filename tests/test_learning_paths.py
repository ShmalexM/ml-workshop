"""Optional onboarding never replaces or resets the learner's existing work."""
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from courses import BY_ID, COURSES, LESSONS
from learning_paths import PROFILE_KEY, profile_from_answers, recommend, saved_profile
from server_fixture import server_token


EXPECTED_PATHS = {
    'explore': ['foundations', 'web', 'data', 'harness'],
    'ml': ['foundations', 'pytorch', 'tensorflow', 'modern'],
    'agents': ['backend', 'harness', 'data', 'reliability'],
    'web': ['backend', 'web', 'interactive', 'reliability'],
    'data': ['data', 'backend', 'reliability'],
}


class RecommendationTests(unittest.TestCase):
    def test_all_experience_and_goal_combinations_are_ordered_and_usable(self):
        courses = {course['id']: course for course in COURSES}
        for experience in ('new', 'some', 'confident'):
            for goal, path in EXPECTED_PATHS.items():
                with self.subTest(experience=experience, goal=goal):
                    profile = profile_from_answers(dict(experience=experience, goal=goal))
                    self.assertEqual(profile, dict(version=1, experience=experience, goal=goal))
                    result = recommend(profile, {})
                    expected = ([] if experience == 'confident' else ['python']) + path
                    self.assertEqual([step['courseId'] for step in result['steps']], expected)
                    self.assertEqual(len(set(expected)), len(expected))
                    assumed = {'python'} if experience == 'confident' else set()
                    for step in result['steps']:
                        course = courses[step['courseId']]
                        self.assertTrue(set(course['orientation']['prerequisites']) <= assumed)
                        assumed.add(course['id'])
                        self.assertTrue(step['reason'].strip())
                        self.assertEqual(step['completed'], 0)
                        self.assertEqual(step['total'], sum(lesson['course'] == course['id'] for lesson in LESSONS))
                        self.assertGreater(step['total'], 0)
                    first = next(lesson['id'] for lesson in LESSONS if lesson['course'] == expected[0])
                    self.assertEqual(result['nextLessonId'], first)
                    self.assertTrue(result['title'].strip())
                    self.assertTrue(result['summary'].strip())
                    self.assertEqual(result['completedLessons'], 0)
                    self.assertEqual(result['totalLessons'], sum(step['total'] for step in result['steps']))
                    self.assertEqual(result, recommend(profile, {}))

    def test_next_lesson_and_counts_follow_step_order_not_completion_order(self):
        profile = profile_from_answers(dict(experience='some', goal='web'))
        completed = {lesson['id'] for lesson in LESSONS if lesson['course'] in ('python', 'web')}
        completed.update(('backend-1', 'backend-3', 'unknown-lesson', 'foundations-1'))
        before = completed.copy()
        result = recommend(profile, completed)
        self.assertEqual(result['nextLessonId'], 'backend-2')
        self.assertEqual([step['completed'] for step in result['steps']], [13, 2, 5, 0, 0])
        self.assertEqual(result['completedLessons'], 20)
        self.assertEqual(completed, before)
        self.assertEqual(profile, dict(version=1, experience='some', goal='web'))

    def test_a_finished_path_has_no_next_lesson_even_with_unrelated_incomplete_courses(self):
        profile = profile_from_answers(dict(experience='confident', goal='data'))
        completed = {lesson['id'] for lesson in LESSONS if lesson['course'] in EXPECTED_PATHS['data']}
        result = recommend(profile, completed)
        self.assertIsNone(result['nextLessonId'])
        self.assertEqual(result['completedLessons'], result['totalLessons'])
        self.assertNotIn('python-1', completed)
        self.assertIsNone(recommend(None, completed))

    def test_profile_input_is_exactly_two_enums_or_explicit_reset(self):
        self.assertIsNone(profile_from_answers({'reset': True}))
        invalid = [None, [], True, 'new', {}, {'experience': 'new'}, {'goal': 'ml'},
                   {'experience': 'expert', 'goal': 'ml'}, {'experience': 'new', 'goal': 'career'},
                   {'experience': True, 'goal': 'ml'}, {'experience': 'new', 'goal': False},
                   {'experience': ['new'], 'goal': 'ml'}, {'experience': 'new', 'goal': {}},
                   {'experience': 'new', 'goal': 'ml', 'version': 1},
                   {'experience': 'new', 'goal': 'ml', 'name': 'unneeded personal text'},
                   {'experience': 'new', 'goal': 'ml', 'reset': True},
                   {'reset': False}, {'reset': 1}, {'reset': 'true'}, {'reset': None},
                   {'reset': True, 'goal': 'ml'}]
        for body in invalid:
            with self.subTest(body=body), self.assertRaises(ValueError):
                profile_from_answers(body)

    def test_corrupt_or_unsupported_saved_profiles_fall_back_without_editing(self):
        with sqlite3.connect(':memory:') as db:
            db.execute('CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)')
            self.assertIsNone(saved_profile(db))
            bad = ['not json', 'null', 'true', '[]', '1', '{}', b'\xff', None,
                   '[' * 1500 + '0' + ']' * 1500,
                   json.dumps(dict(version=True, experience='new', goal='ml')),
                   json.dumps(dict(version=1.0, experience='new', goal='ml')),
                   json.dumps(dict(version=2, experience='new', goal='ml')),
                   json.dumps(dict(version=1, experience='expert', goal='ml')),
                   json.dumps(dict(version=1, experience='new', goal='unknown')),
                   json.dumps(dict(version=1, experience=True, goal='ml')),
                   json.dumps(dict(version=1, experience='new', goal='ml', extra='no'))]
            for value in bad:
                with self.subTest(value=str(value)[:80]):
                    db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (PROFILE_KEY, value))
                    self.assertIsNone(saved_profile(db))
                    self.assertEqual(db.execute('SELECT value FROM settings WHERE key=?', (PROFILE_KEY,)).fetchone()[0], value)


class LearningPathApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='ml-learning-path-test-', ignore_cleanup_errors=True)
        cls.database = Path(cls.tmp.name) / 'workshop.sqlite3'
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            cls.port = sock.getsockname()[1]
        cls.url = f'http://127.0.0.1:{cls.port}'
        cls.start_server()

    @classmethod
    def start_server(cls):
        cls.proc = subprocess.Popen([sys.executable, str(ROOT / 'backend/server.py'), '--port', str(cls.port)],
                                    env={**os.environ, 'ML_WORKSHOP_DATA_DIR': cls.tmp.name},
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        cls.token = server_token(cls.url, cls.tmp.name, cls.proc)

    @classmethod
    def stop_server(cls):
        cls.proc.terminate()
        try:
            cls.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.proc.kill()
            cls.proc.wait()

    @classmethod
    def tearDownClass(cls):
        cls.stop_server()
        cls.tmp.cleanup()

    def setUp(self):
        with sqlite3.connect(self.database) as db:
            for table in ('settings', 'drafts', 'completions', 'activity', 'solution_views'):
                db.execute(f'DELETE FROM {table}')

    def request(self, path, body=None, *, post=False, headers=None):
        payload = json.dumps(body).encode() if post or body is not None else None
        request = urllib.request.Request(self.url + path, data=payload,
                                         headers={'Content-Type': 'application/json', 'X-Workshop-Token': self.token,
                                                  **(headers or {})})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    def test_api_matrix_and_new_learner_default(self):
        self.assertEqual(self.request('/api/learning-path'), dict(profile=None, recommendation=None))
        self.assertEqual(self.request('/api/state')['currentLesson'], 'python-1')
        for experience in ('new', 'some', 'confident'):
            for goal, path in EXPECTED_PATHS.items():
                with self.subTest(experience=experience, goal=goal):
                    result = self.request('/api/learning-path', dict(experience=experience, goal=goal))
                    self.assertEqual(set(result), {'profile', 'recommendation'})
                    self.assertEqual(result['profile'], dict(version=1, experience=experience, goal=goal))
                    self.assertEqual(result, self.request('/api/learning-path'))
                    expected = ([] if experience == 'confident' else ['python']) + path
                    self.assertEqual([step['courseId'] for step in result['recommendation']['steps']], expected)
                    self.assertIn(result['recommendation']['nextLessonId'], BY_ID)

    def test_preferences_persist_across_server_restart(self):
        expected = self.request('/api/learning-path', dict(experience='some', goal='agents'))
        token = self.token
        type(self).stop_server()
        type(self).start_server()
        self.assertEqual(self.token, token)
        self.assertEqual(self.request('/api/learning-path'), expected)
        with sqlite3.connect(self.database) as db:
            saved = json.loads(db.execute('SELECT value FROM settings WHERE key=?', (PROFILE_KEY,)).fetchone()[0])
        self.assertEqual(saved, expected['profile'])

    def test_save_edit_and_reset_preserve_existing_work_and_current_place(self):
        draft = dict(lessonId='web-2', code='// a draft', notes='a useful note', updatedAt=100)
        self.request('/api/draft', draft)
        self.request('/api/current', dict(lessonId='web-2'))
        with sqlite3.connect(self.database) as db:
            db.execute('INSERT INTO completions VALUES (?,?,?)', ('python-1', '2026-01-01T00:00:00Z', 100))
            db.execute('INSERT INTO activity VALUES (?)', ('2026-01-01',))
            db.execute('INSERT INTO settings VALUES (?,?)', ('unrelatedPreference', 'keep'))
        before = self.request('/api/state')
        self.request('/api/learning-path', dict(experience='new', goal='ml'))
        self.assertEqual(self.request('/api/state'), before)
        self.request('/api/learning-path', dict(experience='confident', goal='web'))
        self.assertEqual(self.request('/api/state'), before)
        self.assertEqual(self.request('/api/learning-path', {'reset': True}), dict(profile=None, recommendation=None))
        self.assertEqual(self.request('/api/state'), before)
        with sqlite3.connect(self.database) as db:
            self.assertIsNone(db.execute('SELECT value FROM settings WHERE key=?', (PROFILE_KEY,)).fetchone())
            self.assertEqual(dict(db.execute('SELECT key,value FROM settings')),
                             dict(currentLesson='web-2', unrelatedPreference='keep'))

    def test_only_a_successful_check_advances_the_path(self):
        self.request('/api/learning-path', dict(experience='confident', goal='ml'))
        initial = self.request('/api/learning-path')
        code = 'def predict(x, weight, bias): return x * weight + bias'
        self.request('/api/draft', dict(lessonId='foundations-1', code=code, notes='', updatedAt=100))
        self.request('/api/current', dict(lessonId='foundations-2'))
        self.request('/api/solution/foundations-1')
        self.request('/api/example', dict(lessonId='foundations-1'))
        self.request('/api/run', dict(lessonId='foundations-1', code=code, mode='run'))
        self.request('/api/run', dict(lessonId='foundations-1', code='def predict(x, weight, bias): return 0', mode='check'))
        self.assertEqual(self.request('/api/learning-path'), initial)
        result = self.request('/api/run', dict(lessonId='foundations-1', code=code, mode='check'))
        self.assertTrue(result['passed'])
        changed = self.request('/api/learning-path')['recommendation']
        self.assertEqual(changed['completedLessons'], 1)
        self.assertEqual(changed['steps'][0]['completed'], 1)
        self.assertEqual(changed['nextLessonId'], 'foundations-2')
        # Rechecking one lesson does not add path progress twice.
        self.request('/api/run', dict(lessonId='foundations-1', code=code, mode='check'))
        self.assertEqual(self.request('/api/learning-path')['recommendation'], changed)

    def test_completed_path_returns_null_next_lesson(self):
        self.request('/api/learning-path', dict(experience='new', goal='data'))
        with sqlite3.connect(self.database) as db:
            for lesson in LESSONS:
                if lesson['course'] in ['python', *EXPECTED_PATHS['data']]:
                    db.execute('INSERT INTO completions VALUES (?,?,?)', (lesson['id'], '2026-01-01T00:00:00Z', lesson['xp']))
        result = self.request('/api/learning-path')['recommendation']
        self.assertIsNone(result['nextLessonId'])
        self.assertEqual(result['completedLessons'], result['totalLessons'])
        self.assertLess(result['totalLessons'], len(LESSONS))

    def test_invalid_profiles_are_400_and_keep_the_previous_selection(self):
        expected = self.request('/api/learning-path', dict(experience='new', goal='explore'))
        invalid = [None, [], False, 'ml', {}, {'experience': 'new'}, {'goal': 'ml'},
                   {'experience': True, 'goal': 'ml'}, {'experience': 'new', 'goal': False},
                   {'experience': 'NEW', 'goal': 'ml'}, {'experience': 'new', 'goal': 'unknown'},
                   {'experience': [], 'goal': 'ml'}, {'experience': 'new', 'goal': {}},
                   {'experience': 'new', 'goal': 'ml', 'name': 'no free text'},
                   {'experience': 'new', 'goal': 'ml', 'version': 1},
                   {'reset': False}, {'reset': 1}, {'reset': 'true'}, {'reset': True, 'extra': 1}]
        for body in invalid:
            with self.subTest(body=body), self.assertRaises(urllib.error.HTTPError) as error:
                self.request('/api/learning-path', body, post=True)
            self.assertEqual(error.exception.code, 400)
            self.assertEqual(self.request('/api/learning-path'), expected)

    def test_corrupt_saved_profile_is_safe_and_can_be_replaced_or_reset(self):
        with sqlite3.connect(self.database) as db:
            db.execute('INSERT INTO settings VALUES (?,?)', (PROFILE_KEY, '{broken'))
        before = self.request('/api/state')
        self.assertEqual(self.request('/api/learning-path'), dict(profile=None, recommendation=None))
        self.assertEqual(self.request('/api/state'), before)
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute('SELECT value FROM settings WHERE key=?', (PROFILE_KEY,)).fetchone()[0], '{broken')
        expected = self.request('/api/learning-path', dict(experience='confident', goal='data'))
        self.assertEqual(expected['profile']['goal'], 'data')
        self.request('/api/learning-path', {'reset': True})
        self.assertEqual(self.request('/api/learning-path'), dict(profile=None, recommendation=None))

    def test_profile_is_in_progress_backup_and_reset_exports_null(self):
        selected = self.request('/api/learning-path', dict(experience='some', goal='web'))
        backup = self.request(self.request('/api/backup', {})['url'])
        self.assertEqual(backup['learnerProfile'], selected['profile'])
        self.assertEqual(backup['version'], 3)
        self.assertNotIn('recommendation', backup)
        self.request('/api/learning-path', {'reset': True})
        backup = self.request(self.request('/api/backup', {})['url'])
        self.assertIsNone(backup['learnerProfile'])

    def test_reads_and_writes_require_session_and_same_origin(self):
        for post in (False, True):
            for headers in ({'X-Workshop-Token': ''}, {'X-Workshop-Token': 'wrong'}, {'Host': 'attacker.example'},
                            {'Origin': 'https://example.com'}, {'Sec-Fetch-Site': 'cross-site'}):
                with self.subTest(post=post, headers=headers), self.assertRaises(urllib.error.HTTPError) as error:
                    self.request('/api/learning-path', dict(experience='new', goal='ml') if post else None,
                                 post=post, headers=headers)
                self.assertEqual(error.exception.code, 403)
        self.assertEqual(self.request('/api/learning-path'), dict(profile=None, recommendation=None))


if __name__ == '__main__':
    unittest.main()
