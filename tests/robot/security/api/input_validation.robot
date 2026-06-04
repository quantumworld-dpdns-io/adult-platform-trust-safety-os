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
Oversized Payload
    [Documentation]    Test handling of oversized request payloads
    [Tags]    api    validation    oversized
    ${headers}=    Create Auth Headers
    ${large_payload}=    Evaluate    "x" * 10485760
    ${body}=    Create Dictionary    data=${large_payload}
    ${response}=    Send POST Request    /api/v1/upload    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Server accepted 10MB payload
    ${huge_payload}=    Evaluate    "x" * 104857600
    ${body}=    Create Dictionary    data=${huge_payload}
    ${response}=    Send POST Request    /api/v1/upload    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Server accepted 100MB payload

Invalid JSON
    [Documentation]    Test handling of malformed JSON payloads
    [Tags]    api    validation    invalid_json
    ${headers}=    Create Auth Headers
    Set To Dictionary    ${headers}    Content-Type=application/json
    ${invalid_jsons}=    Create List    {invalid json    {"key": "value"    null    undefined
    ...    {{"nested": {"deep": true}}}    []
    FOR    ${json}    IN    @{invalid_jsons}
        ${response}=    Post Request    api    /api/v1/data    data=${json}    headers=${headers}
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=Invalid JSON accepted: ${json}
    END

SQL Injection In Body
    [Documentation]    Test SQL injection in request body fields
    [Tags]    api    validation    sqli
    ${headers}=    Create Auth Headers
    ${sql_payloads}=    SQL Injection Payloads
    FOR    ${payload}    IN    @{sql_payloads}
        ${body}=    Create Dictionary    name=${payload}    description=${payload}
        ${response}=    Send POST Request    /api/v1/items    body=${body}    headers=${headers}
        Should Not Contain    ${response.text}    syntax error    msg=SQL error in response: ${payload}
        Should Not Contain    ${response.text}    SQL    msg=SQL error in response: ${payload}
    END

XSS In Body
    [Documentation]    Test XSS in request body fields
    [Tags]    api    validation    xss
    ${headers}=    Create Auth Headers
    ${xss_payloads}=    XSS Payloads
    FOR    ${payload}    IN    @{xss_payloads}
        ${body}=    Create Dictionary    title=${payload}    content=${payload}
        ${response}=    Send POST Request    /api/v1/items    body=${body}    headers=${headers}
        ${json}=    Extract Response JSON    ${response}
        ${title}=    Get From Dictionary    ${json}    title    default=${EMPTY}
        Should Not Contain    ${title}    <script>    msg=XSS not sanitized in title: ${payload}
        Should Not Contain    ${title}    onerror=    msg=XSS not sanitized in title: ${payload}
    END

Null Bytes Injection
    [Documentation]    Test null byte injection in request data
    [Tags]    api    validation    null_bytes
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    filename=test.txt%00.jpg
    ${response}=    Send POST Request    /api/v1/files    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Null byte injection accepted in filename
    ${body}=    Create Dictionary    data=test%00data
    ${response}=    Send POST Request    /api/v1/data    body=${body}    headers=${headers}
    Should Not Contain    ${response.text}    test    msg=Null byte data processed

Unicode Exploits
    [Documentation]    Test Unicode-based attacks and normalization issues
    [Tags]    api    validation    unicode
    ${headers}=    Create Auth Headers
    ${unicode_payloads}=    Create List
    ...    \u003cscript\u003ealert(1)\u003c/script\u003e
    ...    \uFEFF<script>alert(1)</script>
    ...    <scr\u0000ipt>alert(1)</script>
    ...    ＜script＞alert(1)＜/script＞
    FOR    ${payload}    IN    @{unicode_payloads}
        ${body}=    Create Dictionary    name=${payload}
        ${response}=    Send POST Request    /api/v1/items    body=${body}    headers=${headers}
        ${json}=    Extract Response JSON    ${response}
        ${name}=    Get From Dictionary    ${json}    name    default=${EMPTY}
        Should Not Contain    ${name}    <script>    msg=Unicode XSS not sanitized
    END

Content Type Mismatch
    [Documentation]    Test handling of content type mismatch
    [Tags]    api    validation    content_type
    ${headers}=    Create Auth Headers
    Set To Dictionary    ${headers}    Content-Type=text/plain
    ${response}=    Post Request    api    /api/v1/data    data=plain text    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Content type mismatch accepted
    Set To Dictionary    ${headers}    Content-Type=application/xml
    ${response}=    Post Request    api    /api/v1/data    data=<root>test</root>    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=XML content accepted on JSON endpoint

Parameter Type Validation
    [Documentation]    Test parameter type validation
    [Tags]    api    validation    type
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    age=not_a_number
    ${response}=    Send POST Request    /api/v1/users    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Invalid type accepted for age field
    ${body}=    Create Dictionary    email=not_an_email
    ${response}=    Send POST Request    /api/v1/users    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Invalid email format accepted
    ${body}=    Create Dictionary    active=yes_please
    ${response}=    Send POST Request    /api/v1/users    body=${body}    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Invalid boolean accepted
