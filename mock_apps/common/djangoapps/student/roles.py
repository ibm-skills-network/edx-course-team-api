class CourseRole:
    def __init__(self, course_key):
        self.course_key = course_key


class CourseInstructorRole(CourseRole):
    ROLE = 'instructor'


class CourseStaffRole(CourseRole):
    ROLE = 'staff'
