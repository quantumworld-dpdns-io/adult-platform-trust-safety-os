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
Missing Auth Header
    [Documentation]    Test API access without authentication header
    [Tags]    api    auth    missing_header
    ${headers}=    Create Dictionary    Content-Type=application/json
    ${response}=    Send GET Request    /api/v1/users/me    headers=${headers}
    Response Status Should Be    ${response}    401
    ${response}=    Send POST Request    /api/v1/users
    ...    body=${None}    headers=${headers}
    Response Status Should Be    ${response}    401
    ${response}=    Send PUT Request    /api/v1/users/me
    ...    body=${None}    headers=${headers}
    Response Status Should Be    ${response}    401
    ${response}=    Send DELETE Request    /api/v1/users/me    headers=${headers}
    Response Status Should Be    ${response}    401

Invalid Token
    [Documentation]    Test API access with invalid authentication token
    [Tags]    api    auth    invalid_token
    ${invalid_tokens}=    Create List    invalidtoken123    abc123    00000000-0000-0000-0000-000000000000
    FOR    ${token}    IN    @{invalid_tokens}
        ${headers}=    Create Auth Headers    ${token}
        ${response}=    Send GET Request    /api/v1/users/me    headers=${headers}
        Response Status Should Be    ${response}    401
    END

Expired Token
    [Documentation]    Test API access with expired authentication token
    [Tags]    api    auth    expired_token
    ${expired_token}=    Generate Malicious JWT    claim_overrides={"exp": 1000000000}
    ${headers}=    Create Auth Headers    ${expired_token}
    ${response}=    Send GET Request    /api/v1/users/me    headers=${headers}
    Response Status Should Be    ${response}    401

Wrong Issuer
    [Documentation]    Test API access with token from wrong issuer
    [Tags]    api    auth    wrong_issuer
    ${wrong_issuer_token}=    Generate Malicious JWT    claim_overrides={"iss": "evil-issuer.com", "sub": "admin"}
    ${headers}=    Create Auth Headers    ${wrong_issuer_token}
    ${response}=    Send GET Request    /api/v1/users/me    headers=${headers}
    Response Status Should Be    ${response}    401

Token Replay Attack
    [Documentation]    Test that tokens cannot be replayed after logout
    [Tags]    api    auth    token_replay
    ${body}=    Create Dictionary    email=test@test.com    password=correctpass
    ${response}=    Send POST Request    /api/v1/auth/login    body=${body}
    ${json}=    Extract Response JSON    ${response}
    ${token}=    Get From Dictionary    ${json}    token    default=${EMPTY}
    IF    "${token}" != "${EMPTY}"
        ${headers}=    Create Auth Headers    ${token}
        ${response}=    Send GET Request    /api/v1/users/me    headers=${headers}
        Response Status Should Be    ${response}    200
        ${response}=    Send POST Request    /api/v1/auth/logout    headers=${headers}
        ${response}=    Send GET Request    /api/v1/users/me    headers=${headers}
        Response Status Should Be    ${response}    401
        ...    msg=Token accepted after logout - replay vulnerability
    END

Token With No Signature
    [Documentation]    Test API access with unsigned JWT
    [Tags]    api    auth    no_signature
    ${unsigned_token}=    Set Variable    eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.
    ${headers}=    Create Auth Headers    ${unsigned_token}
    ${response}=    Send GET Request    /api/v1/users/me    headers=${headers}
    Response Status Should Be    ${response}    401

Token Algorithm Confusion
    [Documentation]    Test for JWT algorithm confusion attacks
    [Tags]    api    auth    algorithm_confusion
    ${alg_confusion_token}=    Generate Malicious JWT    claim_overrides={"alg": "HS256"}
    ${headers}=    Create Auth Headers    ${alg_confusion_token}
    ${response}=    Send GET Request    /api/v1/users/me    headers=${headers}
    Response Status Should Be    ${response}    401
