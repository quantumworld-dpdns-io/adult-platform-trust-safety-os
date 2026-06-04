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
Session Token Prediction
    [Documentation]    Test for predictable session token generation
    [Tags]    functional    session_hijack    prediction
    ${tokens}=    Create List
    FOR    ${i}    IN RANGE    10
        ${body}=    Create Dictionary    email=user${i}@test.com    password=pass123
        ${response}=    Send POST Request    /api/v1/auth/login    body=${body}
        ${token}=    Get From Dictionary    ${response.cookies}    session_id    default=${EMPTY}
        IF    "${token}" != "${EMPTY}"
            Append To List    ${tokens}    ${token}
        END
    END
    ${token_set}=    Evaluate    set($tokens)
    ${unique_count}=    Get Length    ${token_set}
    ${total_count}=    Get Length    ${tokens}
    Should Be Equal As Numbers    ${unique_count}    ${total_count}
    ...    msg=Session tokens are not unique - ${unique_count} unique out of ${total_count}
    FOR    ${token}    IN    @{tokens}
        Length Should Be    ${token}    32    msg=Session token too short: ${token}
    END

Session Fixation Prevention
    [Documentation]    Test that session is regenerated after authentication
    [Tags]    functional    session_hijack    fixation
    ${headers}=    Create Dictionary    Content-Type=application/json
    ${body}=    Create Dictionary    email=test@test.com    password=correctpass
    ${response_1}=    Send POST Request    /api/v1/auth/login    body=${body}    headers=${headers}
    ${session_before}=    Get From Dictionary    ${response_1.cookies}    session_id    default=${EMPTY}
    ${login_headers}=    Create Auth Headers
    ${response_2}=    Send POST Request    /api/v1/auth/login    body=${body}    headers=${login_headers}
    ${session_after}=    Get From Dictionary    ${response_2.cookies}    session_id    default=${EMPTY}
    Should Not Be Equal    ${session_before}    ${session_after}
    ...    msg=Session ID not regenerated after login - fixation vulnerability

Concurrent Session Handling
    [Documentation]    Test concurrent session limits and detection
    [Tags]    functional    session_hijack    concurrent
    ${sessions}=    Create List
    FOR    ${i}    IN RANGE    5
        ${body}=    Create Dictionary    email=test@test.com    password=correctpass
        ${response}=    Send POST Request    /api/v1/auth/login    body=${body}
        ${session_id}=    Get From Dictionary    ${response.cookies}    session_id    default=${EMPTY}
        IF    "${session_id}" != "${EMPTY}"
            Append To List    ${sessions}    ${session_id}
        END
    END
    ${session_count}=    Get Length    ${sessions}
    Should Be True    ${session_count} <= 3    msg=Too many concurrent sessions allowed: ${session_count}

Session Token Entropy
    [Documentation]    Test session token entropy meets security requirements
    [Tags]    functional    session_hijack    entropy
    ${tokens}=    Create List
    FOR    ${i}    IN RANGE    20
        ${body}=    Create Dictionary    email=test@test.com    password=correctpass
        ${response}=    Send POST Request    /api/v1/auth/login    body=${body}
        ${token}=    Get From Dictionary    ${response.cookies}    session_id    default=${EMPTY}
        IF    "${token}" != "${EMPTY}"
            Append To List    ${tokens}    ${token}
        END
    END
    ${token_set}=    Evaluate    set($tokens)
    ${unique_ratio}=    Evaluate    len($token_set) / len($tokens) if len($tokens) > 0 else 0
    Should Be True    ${token_ratio} > 0.9    msg=Session tokens lack entropy - ratio: ${token_ratio}

Session Token Invalidation On Password Change
    [Documentation]    Test that all sessions are invalidated on password change
    [Tags]    functional    session_hijack    password_change
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    current_password=oldpass    new_password=newpass123
    ${response}=    Send POST Request    /api/v1/auth/change-password    body=${body}    headers=${headers}
    Response Status Should Be    ${response}    200
    ${response}=    Send GET Request    /api/v1/users/me    headers=${headers}
    Response Status Should Be    ${response}    401
    ...    msg=Session not invalidated after password change

Session Token Secure Attributes
    [Documentation]    Test session token has secure attributes
    [Tags]    functional    session_hijack    secure_attributes
    ${body}=    Create Dictionary    email=test@test.com    password=correctpass
    ${response}=    Send POST Request    /api/v1/auth/login    body=${body}
    ${cookies}=    Set Variable    ${response.cookies}
    ${session_cookie}=    Get From Dictionary    ${cookies}    session_id    default=${None}
    IF    ${session_cookie} is not None
        Should Be True    ${session_cookie.secure}    msg=Session cookie missing Secure flag
        Should Be Equal    ${session_cookie._rest}[HttpOnly]    True
        ...    msg=Session cookie missing HttpOnly flag
        Should Be Equal    ${session_cookie._rest}[SameSite]    Strict
        ...    msg=Session cookie missing SameSite=Strict
    END

Session Token Not In URL
    [Documentation]    Test that session tokens are not passed in URLs
    [Tags]    functional    session_hijack    url_leakage
    ${headers}=    Create Auth Headers
    ${response}=    Send GET Request    /api/v1/users/me    headers=${headers}
    ${url}=    Set Variable    ${response.url}
    Should Not Contain    ${url}    session_id    msg=Session token found in URL
    Should Not Contain    ${url}    token=    msg=Token parameter found in URL
