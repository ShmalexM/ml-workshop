"""Local, optional learner preferences and deterministic curriculum recommendations."""
import json

from courses import LESSONS

PROFILE_KEY = 'learnerProfile'
PROFILE_VERSION = 1
EXPERIENCES = ('new', 'some', 'confident')
GOALS = ('explore', 'ml', 'agents', 'web', 'data')

# Each sequence respects the existing course prerequisites. Confident learners report
# that they already know Python; everyone else gets the complete Python introduction.
# These are starting suggestions, not locks: the full curriculum stays available.
PATHS = {
    'explore': dict(
        title='Explore coding and AI',
        summary='Try small exercises in machine learning, web apps, data and agent workflows to find what interests you.',
        courses=(
            ('foundations', 'See how a simple model learns from examples before choosing a specialty.'),
            ('web', 'Try JavaScript and the state changes behind a web interface.'),
            ('data', 'Practice preparing text and checking retrieval results.'),
            ('harness', 'Explore the rules that control an agent workflow using recorded data.'),
        )),
    'ml': dict(
        title='Build a machine learning foundation',
        summary='Learn predictions and training first, then use PyTorch, TensorFlow and local AI building blocks.',
        courses=(
            ('foundations', 'Learn predictions, loss and evaluation before working with a framework.'),
            ('pytorch', 'Build on the foundations with tensors, automatic gradients and a training loop.'),
            ('tensorflow', 'Apply the same training ideas in TensorFlow and Keras.'),
            ('modern', 'Use your PyTorch foundation to inspect tokenization, transformers and retrieval locally.'),
        )),
    'agents': dict(
        title='Build reliable agent workflows',
        summary='Practice framework-free request handling, agent control, retrieval and evaluation with local recorded data. These exercises do not call a model service.',
        courses=(
            ('backend', 'Start with validated inputs and repeatable API behavior for agent tools.'),
            ('harness', 'Control run state, allowed tool inputs, budgets and the context each step loads, then evaluate runs.'),
            ('data', 'Prepare and evaluate the retrieved context that an agent workflow can use.'),
            ('reliability', 'Build on backend skills to handle retries, telemetry and release decisions.'),
        )),
    'web': dict(
        title='Build dependable apps',
        summary='Practice request handling, JavaScript interface state and app lifecycle through local functions, then study reliability.',
        courses=(
            ('backend', 'Understand the request contracts and validation that an app depends on.'),
            ('web', 'Learn JavaScript state updates and how to handle asynchronous results.'),
            ('interactive', 'Extend state skills to lifecycle, time and interactive behavior.'),
            ('reliability', 'Use your backend foundation to reason about retries and shipping decisions.'),
        )),
    'data': dict(
        title='Work with data and retrieval',
        summary='Practice framework-free ingestion, text preparation, retrieval evaluation and dependable data services. These exercises do not train a model.',
        courses=(
            ('data', 'Start with duplicate inputs, text chunks and measuring retrieval quality.'),
            ('backend', 'Build the validation and pagination skills used around data pipelines.'),
            ('reliability', 'Build on backend skills to handle retries and measure service behavior.'),
        )),
}


def profile_from_answers(body):
    """Accept exactly two enum answers, or an explicit profile-only reset."""
    if not isinstance(body, dict):
        raise ValueError('Expected an object with experience and goal.')
    if set(body) == {'reset'} and body['reset'] is True:
        return None
    if set(body) != {'experience', 'goal'}:
        raise ValueError('Choose experience and goal, or send reset: true.')
    experience, goal = body['experience'], body['goal']
    if type(experience) is not str or experience not in EXPERIENCES:
        raise ValueError('Choose a valid coding experience level.')
    if type(goal) is not str or goal not in GOALS:
        raise ValueError('Choose a valid learning goal.')
    return dict(version=PROFILE_VERSION, experience=experience, goal=goal)


def saved_profile(db):
    """An unreadable or unsupported setting behaves like unanswered onboarding.

    Leave the original row alone so a read never edits learner data. The learner
    can replace it by answering again, or explicitly reset just this preference.
    """
    row = db.execute('SELECT value FROM settings WHERE key=?', (PROFILE_KEY,)).fetchone()
    if not row:
        return None
    try:
        profile = json.loads(row[0])
        if not isinstance(profile, dict) or set(profile) != {'version', 'experience', 'goal'}:
            return None
        if type(profile['version']) is not int or profile['version'] != PROFILE_VERSION:
            return None
        return profile_from_answers({key: profile[key] for key in ('experience', 'goal')})
    except (ValueError, TypeError, RecursionError):
        return None


def recommend(profile, completed):
    """Derive path progress only from successful lesson completions, never views."""
    if profile is None:
        return None
    path = PATHS[profile['goal']]
    courses = list(path['courses'])
    if profile['experience'] != 'confident':
        reason = ('Start with your first line of code, then practice the Python the other paths use.'
                  if profile['experience'] == 'new' else
                  'Refresh Python functions, lists, loops and errors before the goal-specific exercises.')
        courses.insert(0, ('python', reason))
    steps = []
    next_lesson = None
    for course_id, reason in courses:
        lessons = [lesson['id'] for lesson in LESSONS if lesson['course'] == course_id]
        steps.append(dict(courseId=course_id, reason=reason,
                          completed=sum(lesson_id in completed for lesson_id in lessons), total=len(lessons)))
        if next_lesson is None:
            next_lesson = next((lesson_id for lesson_id in lessons if lesson_id not in completed), None)
    return dict(title=path['title'], summary=path['summary'], steps=steps, nextLessonId=next_lesson,
                completedLessons=sum(step['completed'] for step in steps),
                totalLessons=sum(step['total'] for step in steps))


def state(db):
    profile = saved_profile(db)
    completed = {row[0] for row in db.execute('SELECT lesson FROM completions')}
    return dict(profile=profile, recommendation=recommend(profile, completed))


def save(db, body):
    profile = profile_from_answers(body)
    if profile is None:
        db.execute('DELETE FROM settings WHERE key=?', (PROFILE_KEY,))
    else:
        db.execute('INSERT OR REPLACE INTO settings VALUES (?,?)', (PROFILE_KEY, json.dumps(profile)))
    return state(db)
