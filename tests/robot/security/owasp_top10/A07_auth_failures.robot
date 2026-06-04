*** Settings ***
Library    RequestsLibrary
Library    Collections
Library    String
Library    JSON
Resource    ../resources/api_keywords.robot
Resource    ../resources/security_keywords.robot
Suite Setup    Setup Test Environment
Suite Teardown    Teardown Test Environment
Test Timeout    60s

*** Test Cases ***
Brute Force Protection
    [Documentation]    A07:1 - Test brute force protection on login
    [Tags]    owasp    a07    brute_force
    ${headers}=    Create Dictionary    Content-Type=application/json
    ${locked_out}=    Set Variable    ${False}
    FOR    ${i}    IN RANGE    20
        ${body}=    Create Dictionary    email=test@test.com    password=wrong${i}
        ${response}=    Send POST Request    /api/v1/auth/login    body=${body}    headers=${headers}
        IF    ${response.status_code} == 429
            ${locked_out}=    Set Variable    ${True}
            BREAK
        END
        IF    ${response.status_code} == 423
            ${locked_out}=    Set Variable    ${True}
            BREAK
        END
    END
    Should Be True    ${locked_out}    msg=Account not locked after 20 failed attempts

Session Fixation Prevention
    [Documentation]    A07:2 - Test session fixation prevention
    [Tags]    owasp    a07    session_fixation
    ${body}=    Create Dictionary    email=test@test.com    password=correctpass
    ${response_1}=    Send POST Request    /api/v1/auth/login    body=${body}
    ${session_1}=    Get From Dictionary    ${response_1.cookies}    session_id    default=${EMPTY}
    ${response_2}=    Send POST Request    /api/v1/auth/login    body=${body}
    ${session_2}=    Get From Dictionary    ${response_2.cookies}    session_id    default=${EMPTY}
    Should Not Be Equal    ${session_1}    ${session_2}    msg=Session ID not regenerated after login

Credential Stuffing Protection
    [Documentation]    A07:3 - Test protection against credential stuffing
    [Tags]    owasp    a07    credential_stuffing
    ${headers}=    Create Dictionary    Content-Type=application/json
    ${blocked}=    Set Variable    ${False}
    FOR    ${i}    IN RANGE    30
        ${body}=    Create Dictionary    email=user${i}@test.com    password=password${i}
        ${response}=    Send POST Request    /api/v1/auth/login    body=${body}    headers=${headers}
        IF    ${response.status_code} == 429
            ${blocked}=    Set Variable    ${True}
            BREAK
        END
    END
    Should Be True    ${blocked}    msg=No rate limiting after 30 credential stuffing attempts

Password Policy Validation
    [Documentation]    A07:4 - Test password policy enforcement
    [Tags]    owasp    a07    password_policy
    ${weak_passwords}=    Create List    123456    password    admin    12345678    qwerty
    FOR    ${weak}    IN    @{weak_passwords}
        ${body}=    Create Dictionary    email=newuser@test.com    password=${weak}
        ${response}=    Send POST Request    /api/v1/auth/register    body=${body}
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=Weak password accepted: ${weak}
    END

MFA Bypass Attempt
    [Documentation]    A07:5 - Test MFA bypass attempts
    [Tags]    owasp    a07    mfa_bypass
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    mfa_code=000000
    ${response}=    Send POST Request    /api/v1/auth/mfa/verify    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=MFA bypassed with zero code
    ${body}=    Create Dictionary    mfa_code=123456
    ${response}=    Send POST Request    /api/v1/auth/mfa/verify    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=MFA bypassed with common code

Session Timeout Validation
    [Documentation]    A07:6 - Test session timeout enforcement
    [Tags]    owasp    a07    session_timeout
    ${headers}=    Create Auth Headers
    ${response}=    Send GET Request    /api/v1/config/session    headers=${headers}
    ${json}=    Extract Response JSON    ${response}
    ${timeout}=    Get From Dictionary    ${json}    session_timeout    default=${0}
    Should Be True    ${timeout} <= 3600    msg=Session timeout too long: ${timeout}s (max 1 hour)
    Should Be True    ${timeout} > 0    msg=Session timeout not configured

Remember Me Security
    [Documentation]    A07:7 - Test remember me token security
    [Tags]    owasp    a07    remember_me
    ${body}=    Create Dictionary    email=test@test.com    password=correctpass    remember_me=${True}
    ${response}=    Send POST Request    /api/v1/auth/login    body=${body}
    ${cookies}=    Set Variable    ${response.cookies}
    ${remember_token}=    Get From Dictionary    ${cookies}    remember_token    default=${EMPTY}
    IF    "${remember_token}" != "${EMPTY}"
        Length Should Be    ${remember_token}    64    msg=Remember me token too short
        Should Not Match Regexp    ${remember_token}    ^[a-z]+$    msg=Remember me token not random enough
    END

Logout Server-Side Invalidation
    [Documentation]    A07:8 - Test server-side session invalidation on logout
    [Tags]    owasp    a07    logout
    ${headers}=    Create Auth Headers
    ${response}=    Send POST Request    /api/v1/auth/logout    headers=${headers}
    Response Status Should Be    ${response}    200
    ${response}=    Send GET Request    /api/v1/users/me    headers=${headers}
    Response Status Should Be    ${response}    401    msg=Session not invalidated after logout

Password Reset Token Expiration
    [Documentation]    A07:9 - Test password reset token expiration
    [Tags]    owasp    a07    reset_token
    ${body}=    Create Dictionary    email=test@test.com
    ${response}=    Send POST Request    /api/v1/auth/forgot-password    body=${body}
    ${json}=    Extract Response JSON    ${response}
    ${reset_token}=    Get From Dictionary    ${json}    token    default=${EMPTY}
    IF    "${reset_token}" != "${EMPTY}"
        Length Should Be    ${reset_token}    32    msg=Reset token too short
    END

Concurrent Session Limit
    [Documentation]    A07:10 - Test concurrent session limits
    [Tags]    owasp    a07    concurrent_sessions
    ${sessions}=    Create List
    FOR    ${i}    IN RANGE    5
        ${body}=    Create Dictionary    email=test@test.com    password=correctpass
        ${response}=    Send POST Request    /api/v1/auth/login    body=${body}
        IF    ${response.status_code} == 200
            Append To List    ${sessions}    ${response}
        END
    END
    ${session_count}=    Get Length    ${sessions}
    Should Be True    ${session_count} <= 3    msg=Too many concurrent sessions allowed: ${session_count}
