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
Default Credentials Test
    [Documentation]    A05:1 - Test for default credentials on admin interfaces
    [Tags]    owasp    a05    default_creds
    ${default_creds}=    Create List    admin:admin    admin:password    root:root    admin:123456
    FOR    ${cred}    IN    @{default_creds}
        ${parts}=    Evaluate    $cred.split(':')
        ${body}=    Create Dictionary    username=${parts[0]}    password=${parts[1]}
        ${response}=    Send POST Request    /api/v1/auth/login    body=${body}
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=Default credentials accepted: ${cred}
    END

Directory Listing Test
    [Documentation]    A05:2 - Test for directory listing enabled on web server
    [Tags]    owasp    a05    directory_listing
    ${paths}=    Create List    /static/    /uploads/    /backup/    /config/    /admin/
    FOR    ${path}    IN    @{paths}
        ${response}=    Send GET Request    ${path}
        Should Not Contain    ${response.text}    Index of    msg=Directory listing enabled at ${path}
    END

Error Message Information Leakage
    [Documentation]    A05:3 - Test for verbose error messages leaking information
    [Tags]    owasp    a05    error_leakage
    ${body}=    Create Dictionary    invalid_field=test
    ${response}=    Send POST Request    /api/v1/auth/login    body=${body}
    Should Not Contain    ${response.text}    stack trace    msg=Stack trace exposed in error
    Should Not Contain    ${response.text}    at com.    msg=Java stack trace exposed
    Should Not Contain    ${response.text}    Traceback    msg=Python traceback exposed
    Should Not Contain    ${response.text}    /src/    msg=Source path exposed
    Should Not Contain    ${response.text}    database    msg=Database info exposed

Security Headers Present
    [Documentation]    A05:4 - Verify all required security headers are present
    [Tags]    owasp    a05    security_headers
    ${response}=    Send GET Request    /api/v1/health
    Check Security Headers    ${response}

Unnecessary Features Test
    [Documentation]    A05:5 - Test for unnecessary features enabled
    [Tags]    owasp    a05    unnecessary_features
    ${response}=    Send GET Request    /api/v1/debug
    Response Status Should Be    ${response}    404
    ${response}=    Send GET Request    /api/v1/status
    Should Not Contain    ${response.text}    uptime
    ...    msg=Debug/status endpoint exposed
    ${response}=    Send GET Request    /api/v1/phpinfo.php
    Should Not Contain    ${response.text}    phpinfo    msg=phpinfo endpoint accessible

Stack Trace Hidden
    [Documentation]    A05:6 - Verify stack traces are not exposed to clients
    [Tags]    owasp    a05    stack_trace
    ${headers}=    Create Auth Headers
    ${body}=    Create Dictionary    id=invalid' OR '1'='1
    ${response}=    Send POST Request    /api/v1/items/${body.id}    body=${body}    headers=${headers}
    Should Not Contain    ${response.text}    Traceback    msg=Python traceback exposed
    Should Not Contain    ${response.text}    at line    msg=Line numbers exposed
    Should Not Contain    ${response.text}    stackTrace    msg=Java stackTrace exposed

Server Version Hidden
    [Documentation]    A05:7 - Verify server version information is hidden
    [Tags]    owasp    a05    server_version
    ${response}=    Send GET Request    /api/v1/health
    ${headers}=    Set Variable    ${response.headers}
    ${server}=    Get From Dictionary    ${headers}    Server    default=${EMPTY}
    Should Not Contain    ${server}    Apache/    msg=Apache version exposed
    Should Not Contain    ${server}    nginx/    msg=Nginx version exposed
    Should Not Contain    ${server}    PHP/    msg=PHP version exposed
    Should Not Contain    ${server}    Microsoft-IIS/    msg=IIS version exposed
    ${x_powered}=    Get From Dictionary    ${headers}    X-Powered-By    default=${EMPTY}
    Should Be Empty    ${x_powered}    msg=X-Powered-By header exposed: ${x_powered}

Admin Interface Accessible
    [Documentation]    A05:8 - Test for exposed admin interfaces
    [Tags]    owasp    a05    admin_interface
    ${admin_paths}=    Create List    /admin    /admin/    /admin/login    /administrator
    ...    /wp-admin    /phpmyadmin    /console    /debug    /actuator
    FOR    ${path}    IN    @{admin_paths}
        ${response}=    Send GET Request    ${path}
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=Admin interface accessible at ${path}
    END

CORS Configuration Test
    [Documentation]    A05:9 - Test CORS configuration
    [Tags]    owasp    a05    cors
    ${headers}=    Create Dictionary    Origin=https://evil.com
    ${response}=    Send GET Request    /api/v1/health    headers=${headers}
    ${acao}=    Get From Dictionary    ${response.headers}    Access-Control-Allow-Origin    default=${EMPTY}
    Should Not Be Equal    ${acao}    *    msg=CORS allows any origin
    Should Not Be Equal    ${acao}    https://evil.com    msg=CORS allows evil origin

HTTP Methods Test
    [Documentation]    A05:10 - Test for unnecessary HTTP methods enabled
    [Tags]    owasp    a05    http_methods
    ${methods}=    Create List    TRACE    DEBUG    OPTIONS
    FOR    ${method}    IN    @{methods}
        ${response}=    Send Request    api    ${method}    /api/v1/health
        Should Not Be Equal As Numbers    ${response.status_code}    200
        ...    msg=HTTP method ${method} should be disabled
    END
