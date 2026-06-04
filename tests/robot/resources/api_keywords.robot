*** Keywords ***
Setup Test Environment
    [Documentation]    Initialize test environment with base URL and default headers
    ${base_url}=    Get Variable Value    ${API_BASE_URL}    https://api.adult-platform.local
    Set Global Variable    ${BASE_URL}    ${base_url}
    ${headers}=    Create Dictionary    Content-Type=application/json    Accept=application/json
    Set Global Variable    ${DEFAULT_HEADERS}    ${headers}
    Create Session    api    ${BASE_URL}    verify=${True}    debug=${False}

Teardown Test Environment
    [Documentation]    Clean up test sessions and variables
    Delete All Sessions
    Delete All Variables

Create Auth Headers
    [Documentation]    Create authorization headers with a valid token
    [Arguments]    ${token}=${None}
    IF    ${token} is None
        ${token}=    Get Variable Value    ${AUTH_TOKEN}
    END
    ${headers}=    Create Dictionary    Content-Type=application/json    Accept=application/json    Authorization=Bearer ${token}
    RETURN    ${headers}

Create Admin Auth Headers
    [Documentation]    Create authorization headers with admin token
    ${headers}=    Create Dictionary    Content-Type=application/json    Accept=application/json    Authorization=Bearer ${ADMIN_TOKEN}
    RETURN    ${headers}

Send GET Request
    [Documentation]    Send a GET request to the specified endpoint
    [Arguments]    ${endpoint}    ${headers}=${None}    ${params}=${None}
    IF    ${headers} is None
        ${headers}=    Create Auth Headers
    END
    ${response}=    Get Request    api    ${endpoint}    headers=${headers}    params=${params}
    RETURN    ${response}

Send POST Request
    [Documentation]    Send a POST request with JSON body
    [Arguments]    ${endpoint}    ${body}=${None}    ${headers}=${None}
    IF    ${headers} is None
        ${headers}=    Create Auth Headers
    END
    ${response}=    Post Request    api    ${endpoint}    json=${body}    headers=${headers}
    RETURN    ${response}

Send PUT Request
    [Documentation]    Send a PUT request with JSON body
    [Arguments]    ${endpoint}    ${body}=${None}    ${headers}=${None}
    IF    ${headers} is None
        ${headers}=    Create Auth Headers
    END
    ${response}=    Put Request    api    ${endpoint}    json=${body}    headers=${headers}
    RETURN    ${response}

Send DELETE Request
    [Documentation]    Send a DELETE request
    [Arguments]    ${endpoint}    ${headers}=${None}
    IF    ${headers} is None
        ${headers}=    Create Auth Headers
    END
    ${response}=    Delete Request    api    ${endpoint}    headers=${headers}
    RETURN    ${response}

Response Should Be JSON
    [Documentation]    Verify response content type is JSON
    [Arguments]    ${response}
    Should Contain    ${response.headers}[Content-Type]    application/json

Response Status Should Be
    [Documentation]    Verify response HTTP status code
    [Arguments]    ${response}    ${expected_status}
    Should Be Equal As Numbers    ${response.status_code}    ${expected_status}

Response Body Should Contain
    [Documentation]    Verify response body contains expected string
    [Arguments]    ${response}    ${expected_text}
    Should Contain    ${response.text}    ${expected_text}

Extract Response JSON
    [Documentation]    Parse and return response JSON body
    [Arguments]    ${response}
    ${json}=    Evaluate    json.loads($response.text)    json
    RETURN    ${json}

Response Time Should Be Under
    [Documentation]    Verify response time is under specified milliseconds
    [Arguments]    ${response}    ${max_ms}=5000
    Should Be True    ${response.elapsed.total_seconds() * 1000} < ${max_ms}

Generate Random String
    [Documentation]    Generate a random alphanumeric string
    [Arguments]    ${length}=16
    ${random}=    Evaluate    ''.join(__import__('random').choices(__import__('string').ascii_letters + __import__('string').digits, k=${length}))
    RETURN    ${random}

Generate Test User
    [Documentation]    Create a unique test user and return credentials
    ${email}=    Evaluate    f"test_{__import__('uuid').uuid4().hex[:8]}@test.example.com"
    ${password}=    Generate Random String    length=16
    ${body}=    Create Dictionary    email=${email}    password=${password}    username=testuser_${email}
    ${response}=    Send POST Request    /api/v1/auth/register    body=${body}
    ${json}=    Extract Response JSON    ${response}
    ${user_id}=    Get From Dictionary    ${json}    id    default=${None}
    ${token}=    Get From Dictionary    ${json}    token    default=${None}
    ${user_data}=    Create Dictionary    email=${email}    password=${password}    user_id=${user_id}    token=${token}
    RETURN    ${user_data}
