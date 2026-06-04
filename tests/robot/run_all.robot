*** Settings ***
Library    Collections
Library    OperatingSystem
Suite Setup    Initialize Test Environment
Suite Teardown    Cleanup Test Environment
Test Timeout    60s

*** Variables ***
${BASE_DIR}    ${CURDIR}

*** Test Cases ***
Execute All Security Test Suites
    [Documentation]    Master test runner that executes all security test suites
    [Tags]    master    all_security
    ${suites}=    Create List
    ...    ${BASE_DIR}/security/owasp_top10/A01_broken_access_control.robot
    ...    ${BASE_DIR}/security/owasp_top10/A02_cryptographic_failures.robot
    ...    ${BASE_DIR}/security/owasp_top10/A03_injection.robot
    ...    ${BASE_DIR}/security/owasp_top10/A04_insecure_design.robot
    ...    ${BASE_DIR}/security/owasp_top10/A05_security_misconfiguration.robot
    ...    ${BASE_DIR}/security/owasp_top10/A06_vulnerable_components.robot
    ...    ${BASE_DIR}/security/owasp_top10/A07_auth_failures.robot
    ...    ${BASE_DIR}/security/owasp_top10/A08_data_integrity.robot
    ...    ${BASE_DIR}/security/owasp_top10/A09_logging_failures.robot
    ...    ${BASE_DIR}/security/owasp_top10/A10_ssrf.robot
    ...    ${BASE_DIR}/security/functional/age_verification_bypass.robot
    ...    ${BASE_DIR}/security/functional/consent_bypass.robot
    ...    ${BASE_DIR}/security/functional/audit_log_tamper.robot
    ...    ${BASE_DIR}/security/functional/session_hijack.robot
    ...    ${BASE_DIR}/security/api/authentication_tests.robot
    ...    ${BASE_DIR}/security/api/authorization_tests.robot
    ...    ${BASE_DIR}/security/api/input_validation.robot
    Log    Total suites to execute: ${suites.__len__()}
    FOR    ${suite}    IN    @{suites}
        Log    Executing: ${suite}
    END

*** Keywords ***
Initialize Test Environment
    [Documentation]    Initialize test environment for all security tests
    Log    Initializing security test environment
    Set Global Variable    ${TEST_START_TIME}    ${CURTIME}

Cleanup Test Environment
    [Documentation]    Cleanup after all security tests complete
    Log    Security test execution completed
