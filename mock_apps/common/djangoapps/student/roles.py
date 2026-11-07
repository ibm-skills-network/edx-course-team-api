class _CourseRole:
    def __init__(self, course_key):
        self.course_key = course_key


class CourseInstructorRole(_CourseRole):
    ROLE = 'instructor'


class CourseStaffRole(_CourseRole):
    ROLE = 'staff'
