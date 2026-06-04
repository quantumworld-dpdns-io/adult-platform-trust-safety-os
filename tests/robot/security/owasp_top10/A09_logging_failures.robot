*** Settings ***
Library    RequestsLibrary
Library    Collections
Library    String
Library    JSON
Library    OperatingSystem
Resource    ../resources/api_keywords.robot
Resource    ../resources/security_keywords.robot
Suite Setup    Setup Test Environment
Suite Teardown    Teardown Test Environment
Test Timeout    30s

*** Test Cases ***
Security Event Logged - Failed Login
    [Documentation]    A09:1 - Verify failed login attempts are logged
    [Tags]    owasp    a09    logging    login
    ${body}=    Create Dictionary    email=test@test.com    password=wrongpass
    ${response}=    Send POST Request    /api/v1/auth/login    body=${body}
    ${admin_headers}=    Create Admin Auth Headers
    ${log_response}=    Send GET Request    /api/v1/admin/logs?event=login_failed&limit=1
    ...    headers=${admin_headers}
    Response Status Should Be    ${log_response}    200
    ${json}=    Extract Response JSON    ${log_response}
    ${logs}=    Get From Dictionary    ${json}    logs    default=${EMPTY}
    Should Not Be Empty    ${logs}    msg=Failed login not logged

Security Event Logged - Successful Login
    [Documentation]    A09:2 - Verify successful login attempts are logged
    [Tags]    owasp    a09    logging    login
    ${body}=    Create Dictionary    email=test@test.com    password=correctpass
    ${response}=    Send POST Request    /api/v1/auth/login    body=${body}
    ${admin_headers}=    Create Admin Auth Headers
    ${log_response}=    Send GET Request    /api/v1/admin/logs?event=login_success&limit=1
    ...    headers=${admin_headers}
    Response Status Should Be    ${log_response}    200

Login Failure Logged With Details
    [Documentation]    A09:3 - Verify login failures include sufficient details
    [Tags]    owasp    a09    logging    login_failure
    ${body}=    Create Dictionary    email=test@test.com    password=wrongpass
    ${response}=    Send POST Request    /api/v1/auth/login    body=${body}
    ${admin_headers}=    Create Admin Auth Headers
    ${log_response}=    Send GET Request    /api/v1/admin/logs?event=login_failed&limit=1
    ...    headers=${admin_headers}
    ${json}=    Extract Response JSON    ${log_response}
    ${logs}=    Get From Dictionary    ${json}    logs    default=${EMPTY}
    Should Not Be Empty    ${logs}    msg=No login failure logs found
    ${log_entry}=    Get From List    ${logs}    0
    Dictionary Should Contain Key    ${log_entry}    timestamp    msg=Log missing timestamp
    Dictionary Should Contain Key    ${log_entry}    ip_address    msg=Log missing IP address
    Dictionary Should Contain Key    ${log_entry}    user_agent    msg=Log missing user agent

Privilege Escalation Logged
    [Documentation]    A09:4 - Verify privilege escalation attempts are logged
    [Tags]    owasp    a09    logging    privilege_escalation
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    role=admin
    ${response}=    Send PUT Request    /api/v1/users/me/role    body=${body}    headers=${headers}
    ${admin_headers}=    Create Admin Auth Headers
    ${log_response}=    Send GET Request    /api/v1/admin/logs?event=privilege_escalation&limit=1
    ...    headers=${admin_headers}
    Response Status Should Be    ${log_response}    200

Input Validation Failure Logged
    [Documentation]    A09:5 - Verify input validation failures are logged
    [Tags]    owasp    a09    logging    input_validation
    ${body}=    Create Dictionary    email=invalid-email    password=short
    ${response}=    Send POST Request    /api/v1/auth/register    body=${body}
    ${admin_headers}=    Create Admin Auth Headers
    ${log_response}=    Send GET Request    /api/v1/admin/logs?event=validation_failed&limit=1
    ...    headers=${admin_headers}
    Response Status Should Be    ${log_response}    200

Log Integrity Check
    [Documentation]    A09:6 - Verify log integrity through hash verification
    [Tags]    owasp    a09    log_integrity
    ${admin_headers}=    Create Admin Auth Headers
    ${response}=    Send GET Request    /api/v1/admin/logs/integrity    headers=${admin_headers}
    Response Status Should Be    ${response}    200
    ${json}=    Extract Response JSON    ${response}
    Dictionary Should Contain Key    ${json}    valid    msg=Log integrity check not available
    Should Be True    ${json}[valid]    msg=Log integrity check failed

Audit Trail Completeness
    [Documentation]    A09:7 - Verify audit trail is complete and cannot be bypassed
    [Tags]    owasp    a09    audit_trail
    ${admin_headers}=    Create Admin Auth Headers
    ${response}=    Send GET Request    /api/v1/admin/audit-trail?start=2024-01-01&end=2024-12-31
    ...    headers=${admin_headers}
    Response Status Should Be    ${response}    200
    ${json}=    Extract Response JSON    ${response}
    ${trail}=    Get From Dictionary    ${json}    audit_trail    default=${EMPTY}
    Should Not Be Empty    ${trail}    msg=Audit trail is empty

Sensitive Data Not Logged
    [Documentation]    A09:8 - Verify sensitive data is not included in logs
    [Tags]    owasp    a09    sensitive_data
    ${admin_headers}=    Create Admin Auth Headers
    ${response}=    Send GET Request    /api/v1/admin/logs?limit=100    headers=${admin_headers}
    ${json}=    Extract Response JSON    ${response}
    ${logs}=    Get From Dictionary    ${json}    logs    default=${EMPTY}
    FOR    ${log}    IN    @{logs}
        ${log_str}=    Evaluate    json.dumps($log)    json
        Should Not Match Regexp    ${log_str}    (?i)password
        ...    msg=Password found in log entry
        Should Not Match Regexp    ${log_str}    (?i)credit.?card
        ...    msg=Credit card found in log entry
        Should Not Match Regexp    ${log_str}    \\b\\d{3}[-.]?\\d{3}[-.]?\\d{4}\\b
        ...    msg=Credit card number found in log entry
    END

Log Tampering Detection
    [Documentation]    A09:9 - Verify log tampering is detected
    [Tags]    owasp    a09    log_tampering
    ${admin_headers}=    Create Admin Auth Headers
    ${response}=    Send DELETE Request    /api/v1/admin/logs    headers=${admin_headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Log deletion endpoint accessible
    ${response}=    Send PUT Request    /api/v1/admin/logs
    ...    body=${None}    headers=${admin_headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Log modification endpoint accessible

Log Retention Policy
    [Documentation]    A09:10 - Verify log retention policy meets compliance requirements
    [Tags]    owasp    a09    log_retention
    ${admin_headers}=    Create Admin Auth Headers
    ${response}=    Send GET Request    /api/v1/admin/logs/config    headers=${admin_headers}
    Response Status Should Be    ${response}    200
    ${json}=    Extract Response JSON    ${response}
    ${retention_days}=    Get From Dictionary    ${json}    retention_days    default=${0}
    Should Be True    ${retention_days} >= 90    msg=Log retention too short: ${retention_days} days (min 90)
