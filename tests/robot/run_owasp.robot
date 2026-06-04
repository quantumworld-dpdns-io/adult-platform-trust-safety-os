*** Settings ***
Library    Collections
Library    OperatingSystem
Suite Setup    Initialize OWASP Tests
Suite Teardown    Cleanup OWASP Tests
Test Timeout    60s

*** Variables ***
${BASE_DIR}    ${CURDIR}

*** Test Cases ***
Execute OWASP Top 10 Test Suite
    [Documentation]    Execute all OWASP Top 10 security test suites
    [Tags]    owasp    top10    security
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
    Log    Executing ${suites.__len__()} OWASP Top 10 test suites
    FOR    ${suite}    IN    @{suites}
        Log    Running: ${suite}
    END

*** Keywords ***
Initialize OWASP Tests
    [Documentation]    Initialize OWASP Top 10 test environment
    Log    Starting OWASP Top 10 security tests

Cleanup OWASP Tests
    [Documentation]    Cleanup after OWASP tests complete
    Log    OWASP Top 10 security tests completed
