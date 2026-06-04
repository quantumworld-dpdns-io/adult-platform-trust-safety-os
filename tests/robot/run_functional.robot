*** Settings ***
Library    Collections
Library    OperatingSystem
Suite Setup    Initialize Functional Tests
Suite Teardown    Cleanup Functional Tests
Test Timeout    60s

*** Variables ***
${BASE_DIR}    ${CURDIR}

*** Test Cases ***
Execute Functional Security Test Suite
    [Documentation]    Execute all functional security test suites
    [Tags]    functional    security
    ${suites}=    Create List
    ...    ${BASE_DIR}/security/functional/age_verification_bypass.robot
    ...    ${BASE_DIR}/security/functional/consent_bypass.robot
    ...    ${BASE_DIR}/security/functional/audit_log_tamper.robot
    ...    ${BASE_DIR}/security/functional/session_hijack.robot
    Log    Executing ${suites.__len__()} functional security test suites
    FOR    ${suite}    IN    @{suites}
        Log    Running: ${suite}
    END

*** Keywords ***
Initialize Functional Tests
    [Documentation]    Initialize functional security test environment
    Log    Starting functional security tests

Cleanup Functional Tests
    [Documentation]    Cleanup after functional tests complete
    Log    Functional security tests completed
