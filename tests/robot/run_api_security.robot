*** Settings ***
Library    Collections
Library    OperatingSystem
Suite Setup    Initialize API Security Tests
Suite Teardown    Cleanup API Security Tests
Test Timeout    60s

*** Variables ***
${BASE_DIR}    ${CURDIR}

*** Test Cases ***
Execute API Security Test Suite
    [Documentation]    Execute all API security test suites
    [Tags]    api    security
    ${suites}=    Create List
    ...    ${BASE_DIR}/security/api/authentication_tests.robot
    ...    ${BASE_DIR}/security/api/authorization_tests.robot
    ...    ${BASE_DIR}/security/api/input_validation.robot
    Log    Executing ${suites.__len__()} API security test suites
    FOR    ${suite}    IN    @{suites}
        Log    Running: ${suite}
    END

*** Keywords ***
Initialize API Security Tests
    [Documentation]    Initialize API security test environment
    Log    Starting API security tests

Cleanup API Security Tests
    [Documentation]    Cleanup after API security tests complete
    Log    API security tests completed
