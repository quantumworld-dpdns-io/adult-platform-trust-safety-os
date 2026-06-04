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

*** Test Cases ***
Business Logic Bypass - Price Manipulation
    [Documentation]    A04:1 - Test business logic bypass via price manipulation
    [Tags]    owasp    a04    business_logic
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    product_id=123    price=0.01
    ${response}=    Send POST Request    /api/v1/orders    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Order accepted with manipulated price
    ${body}=    Create Dictionary    product_id=123    quantity=-1
    ${response}=    Send POST Request    /api/v1/orders    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Order accepted with negative quantity

Rate Limiting Test
    [Documentation]    A04:2 - Test rate limiting on sensitive endpoints
    [Tags]    owasp    a04    rate_limiting
    Check Rate Limiting    /api/v1/auth/login    max_requests=10    window_seconds=60
    Check Rate Limiting    /api/v1/auth/register    max_requests=5    window_seconds=60

Password Reset Abuse
    [Documentation]    A04:3 - Test password reset abuse via email bombing
    [Tags]    owasp    a04    password_reset
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    email=test@test.com
    ${count}=    Set Variable    ${0}
    FOR    ${i}    IN RANGE    10
        ${response}=    Send POST Request    /api/v1/auth/forgot-password    body=${body}
        ${count}=    Evaluate    ${count} + 1
    END
    Should Be Equal As Numbers    ${count}    10    msg=Password reset not rate limited

Account Enumeration - Registration
    [Documentation]    A04:4 - Test for user enumeration via registration
    [Tags]    owasp    a04    enumeration
    ${existing_user}=    Generate Test User
    ${body}=    Create Dictionary    email=${existing_user.email}    password=newpass123
    ${response}=    Send POST Request    /api/v1/auth/register    body=${body}
    ${error_msg_1}=    Set Variable    ${response.text}
    ${body}=    Create Dictionary    email=nonexistent@test.com    password=newpass123
    ${response}=    Send POST Request    /api/v1/auth/register    body=${body}
    ${error_msg_2}=    Set Variable    ${response.text}
    Should Be Equal    ${error_msg_1}    ${error_msg_2}    msg=Different error messages allow account enumeration

Account Enumeration - Login
    [Documentation]    A04:5 - Test for user enumeration via login
    [Tags]    owasp    a04    enumeration
    ${body}=    Create Dictionary    email=existing@test.com    password=wrongpass
    ${response}=    Send POST Request    /api/v1/auth/login    body=${body}
    ${error_msg_1}=    Set Variable    ${response.text}
    ${body}=    Create Dictionary    email=nonexistent@test.com    password=wrongpass
    ${response}=    Send POST Request    /api/v1/auth/login    body=${body}
    ${error_msg_2}=    Set Variable    ${response.text}
    Should Be Equal    ${error_msg_1}    ${error_msg_2}    msg=Different error messages allow login enumeration

Resource Consumption Test
    [Documentation]    A04:6 - Test for resource consumption vulnerabilities
    [Tags]    owasp    a04    resource_consumption
    ${headers}=    Create Auth Headers
    ${large_payload}=    Evaluate    "x" * 10485760
    ${body}=    Create Dictionary    data=${large_payload}
    ${response}=    Send POST Request    /api/v1/upload    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Server accepted oversized payload
    ${body}=    Create Dictionary    query=SELECT * FROM users WHERE id IN (${",".join([str(i) for i in range(10000)])})
    ${response}=    Send POST Request    /api/v1/search    body=${body}    headers=${headers}
    Response Time Should Be Under    ${response}    max_ms=10000

Insufficient Anti-Automation
    [Documentation]    A04:7 - Test for insufficient anti-automation controls
    [Tags]    owasp    a04    anti_automation
    ${headers}=    Create Auth Headers
    ${count}=    Set Variable    ${0}
    FOR    ${i}    IN RANGE    50
        ${body}=    Create Dictionary    email=test@test.com    password=pass123
        ${response}=    Send POST Request    /api/v1/auth/login    body=${body}    headers=${headers}
        IF    ${response.status_code} == 429
            Should Be True    ${count} < 20    msg=No CAPTCHA or rate limit after ${count} attempts
            BREAK
        END
        ${count}=    Evaluate    ${count} + 1
    END

Business Logic Bypass - Step Skipping
    [Documentation]    A04:8 - Test business logic bypass by skipping workflow steps
    [Tags]    owasp    a04    workflow
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    step=final    approval=true
    ${response}=    Send POST Request    /api/v1/verification/complete    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Workflow step skipping succeeded

Business Logic Bypass - Race Condition
    [Documentation]    A04:9 - Test race condition in balance operations
    [Tags]    owasp    a04    race_condition
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    amount=100
    ${responses}=    Create List
    FOR    ${i}    IN RANGE    10
        ${response}=    Send POST Request    /api/v1/wallet/withdraw    body=${body}    headers=${headers}
        Append To List    ${responses}    ${response}
    END
    FOR    ${resp}    IN    @{responses}
        Should Not Be Equal As Numbers    ${resp.status_code}    200
    END
