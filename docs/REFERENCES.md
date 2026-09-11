# 참고 자료 및 적용 범위

프로젝트의 계산식과 용어를 특정 기업의 내부 기준으로 오해하지 않도록, 공개 자료와 프로젝트 자체 가정을 구분합니다.

## 1. Capacity Requirements Planning

### Oracle — Overview of Capacity Requirements Planning
https://docs.oracle.com/cd/A60725_05/html/comnls/us/crp/ccrp.htm

Oracle은 CRP를 MRP 계획의 capacity requirements를 충족할 sufficient capacity available이 있는지 검증하고, required capacity와 available capacity를 균형화하는 생산능력 계획 도구로 설명합니다.

### Oracle Capacity User's Guide
https://docs.oracle.com/cd/E18727_01/doc.121/e15189/T473818T474891.htm

Required/available capacity가 시간 단위로 관리될 수 있다는 설명을 참고했습니다.

### 프로젝트 적용 범위
본 프로젝트에서는 위 개념을 단순화하여 다음과 같이 구현했습니다.

- 계획 소요공수 = 계획수량 × 단위 표준공수
- 계획 부하율 = 계획 소요공수 ÷ 가용공수 × 100
- 계획 소요공수 > 가용공수 → 과부하

`100% 초과`는 위험등급이 아니라, 프로젝트 정의상 필요한 계획 공수가 가용공수를 초과한다는 계산적 의미입니다.

---


## 2. 프로젝트 자체 가정

아래 값은 기업 내부 기준이 아니라 가상 데이터 설계를 위한 프로젝트 입력값입니다.

- 부품별 계획수량
- 실제 생산수량
- 불량수량
- 계획/실제 완료일
- 실제 작업공수
- 단위 표준공수
- 가용공수

또한 `Bottleneck 검토 대상`은 실제 기업의 공식 판정 로직이 아닙니다. 계획상 과부하와 실제 생산 미달/일정 지연이 함께 나타나는 항목을 생산관리자가 우선 확인하도록 만든 검토 로직입니다.
