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
