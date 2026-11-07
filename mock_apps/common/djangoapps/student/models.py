class CourseEnrollment:
    @classmethod
    def enroll(cls, user, course_key, mode=None, check_access=False, can_upgrade=False, enterprise_uuid=None):
        pass

    @classmethod
    def unenroll(cls, user, course_id, skip_refund=False):
        pass
