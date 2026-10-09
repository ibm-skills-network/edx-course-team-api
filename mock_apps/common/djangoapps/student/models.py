class CourseEnrollment:
    @classmethod
    def enroll(cls, user, course_key, mode=None, check_access=False, can_upgrade=False):
        pass

    @classmethod
    def unenroll(cls, user, course_key, skip_refund=False):
        pass
