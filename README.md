# edx_course_team_api

Exposes API to add course team member in Studio.

## Usage

### Base Url

`${STUDIO_URL}/sn-api`

### Add course team member

`POST /course-team/<course_key>/modify_access`

The JSON body requires two parameters.

-   `email`: An existed user.
-   `role`: One of `staff`, `instructor`.

Sample request

```json
{
    "email": "instructor@example.com",
    "role": "instructor"
}
```

Sample response

```json
{
    "message": "User is added to course-v1:IBMDeveloperSkillsNetwork+CB0103EN+v1333."
}
```

## Implementation

The handler is taken from [edx/edx-platform/cms/djangoapps/contentstore/views/user.py](https://github.com/edx/edx-platform/blob/d9a072af26ddb87295aa450bea384bc643ad0e50/cms/djangoapps/contentstore/views/user.py#L102-L198).
