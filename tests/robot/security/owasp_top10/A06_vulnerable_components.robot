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
Test Timeout    60s

*** Test Cases ***
Known CVE Check - NPM Dependencies
    [Documentation]    A06:1 - Check npm dependencies for known CVEs
    [Tags]    owasp    a06    cve    npm
    ${result}=    Run Process    npm    audit    --json    shell=${True}
    ...    cwd=${CURDIR}/../../../../    timeout=120s
    IF    ${result.rc} != 0
        Should Not Contain    ${result.stdout}    "critical"
        ...    msg=Critical CVEs found in npm dependencies
        Should Not Contain    ${result.stdout}    "high"
        ...    msg=High severity CVEs found in npm dependencies
    END

Known CVE Check - Python Dependencies
    [Documentation]    A06:2 - Check Python dependencies for known CVEs
    [Tags]    owasp    a06    cve    python
    ${result}=    Run Process    pip-audit    --format=json    shell=${True}
    ...    cwd=${CURDIR}/../../../../    timeout=120s
    IF    ${result.rc} != 0
        Should Not Contain    ${result.stdout}    "critical"
        ...    msg=Critical CVEs found in Python dependencies
    END

Dependency Audit - Package Lock Verification
    [Documentation]    A06:3 - Verify package lock files are present and up to date
    [Tags]    owasp    a06    dependency_audit
    ${project_root}=    Set Variable    ${CURDIR}/../../../../
    File Should Exist    ${project_root}/package-lock.json    msg=package-lock.json missing
    File Should Exist    ${project_root}/requirements.txt    msg=requirements.txt missing
    ${npm_lock_age}=    Run Process    stat    -f%m    ${project_root}/package-lock.json    shell=${True}
    ${pip_req_age}=    Run Process    stat    -f%m    ${project_root}/requirements.txt    shell=${True}
    Should Not Be Empty    ${npm_lock_age.stdout}    msg=Cannot determine package-lock.json age

Outdated Library Detection
    [Documentation]    A06:4 - Check for outdated libraries with known vulnerabilities
    [Tags]    owasp    a06    outdated
    ${result}=    Run Process    npm    outdated    --json    shell=${True}
    ...    cwd=${CURDIR}/../../../../    timeout=60s
    IF    ${result.stdout} != "{}"
        Should Not Contain    ${result.stdout}    "critical"
        ...    msg=Critical outdated libraries found
    END
    ${pip_outdated}=    Run Process    pip    list    --outdated    --format=json    shell=${True}
    ...    cwd=${CURDIR}/../../../../    timeout=60s
    IF    ${pip_outdated.stdout} != "[]"
        Should Not Contain    ${pip_outdated.stdout}    "critical"
        ...    msg=Critical outdated Python packages found
    END

Unused Dependencies Detection
    [Documentation]    A06:5 - Detect unused dependencies that may indicate security risk
    [Tags]    owasp    a06    unused_deps
    ${project_root}=    Set Variable    ${CURDIR}/../../../../
    File Should Exist    ${project_root}/package.json    msg=package.json missing
    ${result}=    Run Process    npx    depcheck    --json    shell=${True}
    ...    cwd=${project_root}    timeout=120s
    IF    ${result.rc} == 0
        Should Not Contain    ${result.stdout}    "dependencies"
        ...    msg=Unused dependencies detected - review for security risk
    END

Transitive Dependency Check
    [Documentation]    A06:6 - Check transitive dependencies for vulnerabilities
    [Tags]    owasp    a06    transitive
    ${result}=    Run Process    npm    audit    --production    shell=${True}
    ...    cwd=${CURDIR}/../../../../    timeout=120s
    Should Not Contain    ${result.stdout}    "critical"
    ...    msg=Critical vulnerabilities in transitive dependencies

License Compliance Check
    [Documentation]    A06:7 - Check for restrictive licenses in dependencies
    [Tags]    owasp    a06    license
    ${result}=    Run Process    npx    license-checker    --json    shell=${True}
    ...    cwd=${CURDIR}/../../../../    timeout=120s
    ${restricted_licenses}=    Create List    GPL-3.0    AGPL-3.0    SSPL-1.0
    FOR    ${license}    IN    @{restricted_licenses}
        Should Not Contain    ${result.stdout}    ${license}
        ...    msg=Restricted license found: ${license}
    END

Container Image Vulnerability Scan
    [Documentation]    A06:8 - Scan container images for vulnerabilities
    [Tags]    owasp    a06    container
    ${result}=    Run Process    trivy    image    --severity    CRITICAL,HIGH    --exit-code    1
    ...    adult-platform:latest    shell=${True}    timeout=300s
    Should Be Equal As Numbers    ${result.rc}    0    msg=Critical vulnerabilities found in container image

API Version Deprecation Check
    [Documentation]    A06:9 - Check for deprecated API versions with known issues
    [Tags]    owasp    a06    api_version
    ${headers}=    Create Auth Headers
    ${response}=    Send GET Request    /api/v1/deprecated    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Deprecated API version still accessible
    ${response}=    Send GET Request    /api/v0/    headers=${headers}
    Should Not Be Equal As Numbers    ${response.status_code}    200
    ...    msg=Legacy API version v0 still accessible
