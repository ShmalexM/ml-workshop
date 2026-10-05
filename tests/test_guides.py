"""Worked examples must run as shown and must not masquerade as completion."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from courses import COURSES,LESSONS
from runner import execute
from test_curriculum import OFFLINE_PREFIX,JS_OFFLINE_PREFIX,require_lesson_modules

class GuideTests(unittest.TestCase):
    def test_every_example_prints_the_teaching_result(self):
        for lesson in LESSONS:
            with self.subTest(lesson=lesson['id']):
                require_lesson_modules(self, lesson)
                example=lesson['example'];lang=lesson.get('language','python')
                prefix=JS_OFFLINE_PREFIX if lang=='javascript' else OFFLINE_PREFIX
                result=execute(prefix+example['code'],[],language=lang,simulator=lesson['course']=='cuda')
                self.assertIsNone(result['error'],result)
                self.assertEqual(result['stdout'].strip(),example['output'],result)
                self.assertFalse(result['passed'])
                print(lesson['id']+': example output verified',flush=True)
    def test_orientation_and_prediction_questions(self):
        course_ids={course['id'] for course in COURSES}
        for course in COURSES:
            self.assertEqual(len(course['orientation']['terms']),3)
            self.assertTrue(set(course['orientation']['prerequisites'])<=course_ids)
            self.assertNotIn(course['id'],course['orientation']['prerequisites'])
        for lesson in LESSONS:
            guide=lesson['example']
            self.assertEqual(len(guide['choices']),3)
            self.assertIn(guide['answer'],range(3))
            self.assertTrue(guide['feedback'] and guide['question'])
            self.assertEqual(len(guide['steps']),2)
if __name__=='__main__':unittest.main()
