export type LearnerExperience = 'new' | 'some' | 'confident'
export type LearnerGoal = 'explore' | 'ml' | 'agents' | 'web' | 'data'
export type LearnerProfile = {version: 1; experience: LearnerExperience; goal: LearnerGoal}
export type LearningPathRecommendation = {
  title: string
  summary: string
  steps: {courseId: string; reason: string; completed: number; total: number}[]
  nextLessonId: string | null
  completedLessons: number
  totalLessons: number
}
export type LearningPathResponse = {profile: LearnerProfile | null; recommendation: LearningPathRecommendation | null}
