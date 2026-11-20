app_name = "deen_hr"
app_title = "DEEN HR"
app_publisher = "Sajid Islam"
app_description = "Custom Frappe HR extensions and biometric integrations for DEEN HR"
app_email = "saajiidi@gmail.com"
app_license = "MIT"

# Apps required for this custom app to function
required_apps = ["hrms"]

# Fixtures to be exported and installed across environments
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [["module", "=", "Deen HR"]],
    },
    {
        "dt": "Shift Type",
        "filters": [["name", "in", ["General Shift - DEEN HR"]]],
    },
    {
        "dt": "Leave Type",
        "filters": [
            [
                "leave_type_name",
                "in",
                ["Casual Leave", "Medical / Sick Leave", "Annual / Earned Leave"],
            ]
        ],
    },
]

# Document Events
# Hook on document methods and events
# doc_events = {
#     "Employee Checkin": {
#         "after_insert": "deen_hr.api.on_employee_checkin"
#     }
# }
