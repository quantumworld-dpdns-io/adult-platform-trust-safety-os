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
SQL Injection - Login Bypass
    [Documentation]    A03:1 - Test SQL injection in login form
    [Tags]    owasp    a03    sqli    login
    ${payloads}=    SQL Injection Payloads
    FOR    ${payload}    IN    @{payloads}
        ${body}=    Create Dictionary    email=${payload}    password=anything
        ${response}=    Send POST Request    /api/v1/auth/login    body=${body}
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=SQL injection succeeded with payload: ${payload}
    END

SQL Injection - Search Parameter
    [Documentation]    A03:2 - Test SQL injection in search parameters
    [Tags]    owasp    a03    sqli    search
    ${payloads}=    SQL Injection Payloads
    FOR    ${payload}    IN    @{payloads}
        ${headers}=    Create Auth Headers
        ${response}=    Send GET Request    /api/v1/search?q=${payload}    headers=${headers}
        Should Not Contain    ${response.text}    syntax error    msg=SQL error exposed for payload: ${payload}
        Should Not Contain    ${response.text}    mysql    msg=MySQL error exposed
        Should Not Contain    ${response.text}    sqlite    msg=SQLite error exposed
        Should Not Contain    ${response.text}    postgresql    msg=PostgreSQL error exposed
    END

SQL Injection - Query Parameters
    [Documentation]    A03:3 - Test SQL injection in various query parameters
    [Tags]    owasp    a03    sqli    parameters
    ${payloads}=    SQL Injection Payloads
    ${params}=    Create List    id    user_id    category    sort    order
    FOR    ${param}    IN    @{params}
        FOR    ${payload}    IN    @{payloads}
            ${headers}=    Create Auth Headers
            ${response}=    Send GET Request    /api/v1/items?${param}=${payload}    headers=${headers}
            Should Not Contain    ${response.text}    SQL    msg=SQL error in ${param}: ${payload}
        END
    END

NoSQL Injection - Login
    [Documentation]    A03:4 - Test NoSQL injection in login
    [Tags]    owasp    a03    nosql
    ${payloads}=    Create List    {"$ne": ""}    {"$gt": ""}    {"$regex": ".*"}    {"$exists": true}
    FOR    ${payload}    IN    @{payloads}
        ${body}=    Create Dictionary    email=${payload}    password=${payload}
        ${response}=    Send POST Request    /api/v1/auth/login    body=${body}
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=NoSQL injection succeeded with payload: ${payload}
    END

NoSQL Injection - Query Parameters
    [Documentation]    A03:5 - Test NoSQL injection in query parameters
    [Tags]    owasp    a03    nosql    query
    ${payloads}=    Create List    {"$ne": null}    {"$gt": ""}    {"$where": "function(){return true}"}
    FOR    ${payload}    IN    @{payloads}
        ${headers}=    Create Auth Headers
        ${response}=    Send GET Request    /api/v1/users?filter=${payload}    headers=${headers}
        Should Not Contain    ${response.text}    MongoError    msg=NoSQL error exposed: ${payload}
    END

LDAP Injection
    [Documentation]    A03:6 - Test LDAP injection in authentication
    [Tags]    owasp    a03    ldap
    ${payloads}=    LDAP Injection Payloads
    FOR    ${payload}    IN    @{payloads}
        ${body}=    Create Dictionary    username=${payload}    password=anything
        ${response}=    Send POST Request    /api/v1/auth/ldap    body=${body}
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=LDAP injection succeeded with payload: ${payload}
        Should Not Contain    ${response.text}    LDAP    msg=LDAP error exposed
    END

OS Command Injection
    [Documentation]    A03:7 - Test OS command injection
    [Tags]    owasp    a03    command_injection
    ${payloads}=    Command Injection Payloads
    FOR    ${payload}    IN    @{payloads}
        ${headers}=    Create Auth Headers
        ${body}=    Create Dictionary    filename=test.txt;${payload}
        ${response}=    Send POST Request    /api/v1/files/process    body=${body}    headers=${headers}
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=Command injection may have succeeded: ${payload}
    END

Template Injection
    [Documentation]    A03:8 - Test server-side template injection
    [Tags]    owasp    a03    ssti
    ${payloads}=    Create List    {{7*7}}    ${7*7}    <%= 7*7 %>    #{7*7}    [[7*7]]
    FOR    ${payload}    IN    @{payloads}
        ${headers}=    Create Auth Headers
        ${body}=    Create Dictionary    template=${payload}
        ${response}=    Send POST Request    /api/v1/templates/render    body=${body}    headers=${headers}
        Should Not Contain    ${response.text}    49    msg=Template injection may have succeeded: ${payload}
    END

ORM Injection
    [Documentation]    A03:9 - Test ORM injection through serialized objects
    [Tags]    owasp    a03    orm
    ${payloads}=    Create List    {"$gt":""}    {"$ne":null}    {"$regex":".*"}    {"$where":"1==1"}
    FOR    ${payload}    IN    @{payloads}
        ${headers}=    Create Auth Headers
        ${body}=    Create Dictionary    filter=${payload}
        ${response}=    Send POST Request    /api/v1/users/search    body=${body}    headers=${headers}
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=ORM injection may have succeeded: ${payload}
    END

Second Order Injection
    [Documentation]    A03:10 - Test second order SQL injection
    [Tags]    owasp    a03    second_order
    ${headers}=    Create Auth Headers
    ${malicious_name}=    Set Variable    admin'--
    ${body}=    Create Dictionary    username=${malicious_name}
    ${response}=    Send POST Request    /api/v1/users/register    body=${body}
    ${response}=    Send GET Request    /api/v1/users?search=${malicious_name}    headers=${headers}
    Should Not Contain    ${response.text}    SQL    msg=Second order injection error exposed
