*** Settings ***
Library    RequestsLibrary
Library    Collections
Library    String
Library    JSON
Resource    ../resources/api_keywords.robot
Resource    ../resources/security_keywords.robot
Suite Setup    Setup Test Environment
Suite Teardown    Teardown Test Environment
Test Timeout    30s

*** Variables ***
${TEST_USER_1_TOKEN}
${TEST_USER_2_TOKEN}
${ADMIN_TOKEN}
${TEST_USER_1_ID}
${TEST_USER_2_ID}

*** Test Cases ***
IDOR Test - Access Other User Data
    [Documentation]    A01:1 - Test for Insecure Direct Object References
    [Tags]    owasp    a01    idor
    ${headers1}=    Create Auth Headers    ${TEST_USER_1_TOKEN}
    ${response}=    Send GET Request    /api/v1/users/${TEST_USER_2_ID}    headers=${headers1}
    Response Status Should Be    ${response}    403
    ${json}=    Extract Response JSON    ${response}
    Dictionary Should Contain Key    ${json}    error

Privilege Escalation Test - User To Admin
    [Documentation]    A01:2 - Test for privilege escalation from user to admin
    [Tags]    owasp    a01    privilege_escalation
    ${headers}=    Create Auth Headers    ${TEST_USER_1_TOKEN}
    ${body}=    Create Dictionary    role=admin
    ${response}=    Send PUT Request    /api/v1/users/${TEST_USER_1_ID}/role    body=${body}    headers=${headers}
    Response Status Should Be    ${response}    403
    ${body}=    Create Dictionary    is_admin=${True}
    ${response}=    Send PUT Request    /api/v1/users/${TEST_USER_1_ID}    body=${body}    headers=${headers}
    Response Status Should Be    ${response}    403

CORS Misconfiguration Test
    [Documentation]    A01:3 - Test for CORS misconfiguration allowing any origin
    [Tags]    owasp    a01    cors
    ${headers}=    Create Dictionary    Origin=https://evil.com    Content-Type=application/json
    ${response}=    Send GET Request    /api/v1/users/me    headers=${headers}
    ${access_control}=    Get From Dictionary    ${response.headers}    Access-Control-Allow-Origin    default=${EMPTY}
    Should Not Be Equal    ${access_control}    *    msg=CORS allows any origin
    Should Not Be Equal    ${access_control}    https://evil.com    msg=CORS allows evil origin

Forced Browsing Test
    [Documentation]    A01:4 - Test for access to admin endpoints without proper authorization
    [Tags]    owasp    a01    forced_browsing
    ${headers}=    Create Auth Headers    ${TEST_USER_1_TOKEN}
    ${response}=    Send GET Request    /api/v1/admin/dashboard    headers=${headers}
    Response Status Should Be    ${response}    403
    ${response}=    Send GET Request    /api/v1/admin/users    headers=${headers}
    Response Status Should Be    ${response}    403
    ${response}=    Send GET Request    /api/v1/admin/settings    headers=${headers}
    Response Status Should Be    ${response}    403

Missing Function Level Access Control Test
    [Documentation]    A01:5 - Test for missing function-level access control
    [Tags]    owasp    a01    access_control
    ${no_auth_headers}=    Create Dictionary    Content-Type=application/json
    ${response}=    Send DELETE Request    /api/v1/users/${TEST_USER_2_ID}    headers=${no_auth_headers}
    Response Status Should Be    ${response}    401
    ${headers}=    Create Auth Headers    ${TEST_USER_1_TOKEN}
    ${response}=    Send DELETE Request    /api/v1/users/${TEST_USER_2_ID}    headers=${headers}
    Response Status Should Be    ${response}    403

JWT Token Manipulation Test
    [Documentation]    A01:6 - Test JWT token manipulation attacks
    [Tags]    owasp    a01    jwt
    ${tampered_token}=    Generate Malicious JWT    claim_overrides={"sub": "admin", "role": "admin"}
    ${headers}=    Create Auth Headers    ${tampered_token}
    ${response}=    Send GET Request    /api/v1/admin/dashboard    headers=${headers}
    Response Status Should Be    ${response}    401
    ${no_alg_token}=    Set Variable    eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhZG1pbiIsImlhdCI6MTUxNjIzOTAyMiwiZXhwIjo5OTk5OTk5OTk5fQ.
    ${headers}=    Create Auth Headers    ${no_alg_token}
    ${response}=    Send GET Request    /api/v1/admin/dashboard    headers=${headers}
    Response Status Should Be    ${response}    401

Horizontal Privilege Escalation Via Parameter Tampering
    [Documentation]    A01:7 - Test horizontal privilege escalation via parameter tampering
    [Tags]    owasp    a01    horizontal_escalation
    ${headers}=    Create Auth Headers    ${TEST_USER_1_TOKEN}
    ${body}=    Create Dictionary    user_id=${TEST_USER_2_ID}
    ${response}=    Send POST Request    /api/v1/users/profile    body=${body}    headers=${headers}
    Response Status Should Be    ${response}    403

Vertical Privilege Escalation Via Header Injection
    [Documentation]    A01:8 - Test vertical privilege escalation via header injection
    [Tags]    owasp    a01    vertical_escalation
    ${headers}=    Create Auth Headers    ${TEST_USER_1_TOKEN}
    Set To Dictionary    ${headers}    X-Admin=true
    ${response}=    Send GET Request    /api/v1/admin/users    headers=${headers}
    Response Status Should Be    ${response}    403
    Set To Dictionary    ${headers}    X-Forwarded-For=127.0.0.1
    ${response}=    Send GET Request    /api/v1/admin/users    headers=${headers}
    Response Status Should Be    ${response}    403

*** Keywords ***
Setup IDOR Test Data
    ${user1}=    Generate Test User
    Set Global Variable    ${TEST_USER_1_TOKEN}    ${user1.token}
    Set Global Variable    ${TEST_USER_1_ID}    ${user1.user_id}
    ${user2}=    Generate Test User
    Set Global Variable    ${TEST_USER_2_TOKEN}    ${user2.token}
    Set Global Variable    ${TEST_USER_2_ID}    ${user2.user_id}
