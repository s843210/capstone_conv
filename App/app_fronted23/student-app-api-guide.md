# Student App API Guide
React Native 앱에서 학생 상품 신청 기능을 연결하기 위한 백엔드 API 가이드입니다.

## Base URL
개발 환경에 맞는 주소를 사용합니다.

| 환경 | Base URL |
|---|---|
| Android Emulator | `http://10.0.2.2:8080` |
| iOS Simulator | `http://localhost:8080` |
| 실제 휴대폰 | `http://백엔드컴퓨터IP:8080` |
| ngrok | `https://xxxx.ngrok-free.app` |

Swagger 문서:

```txt
http://localhost:8080/swagger-ui/index.html
```

## 전체 흐름

```txt
1. 앱이 GET /api/student/products 호출
2. 앱 화면에 상품명 표시
3. 사용자가 원하는 상품과 수량 선택
4. 앱이 POST /api/student/requests 호출
5. 백엔드가 학생 신청 내역 저장
6. 대시보드는 GET /api/student/requests로 신청 현황 조회
```

## 1. 상품 목록 조회

학생이 신청할 수 있는 상품 목록을 가져옵니다.

```http
GET /api/student/products
```

### React Native 예시

```js
const BASE_URL = "http://10.0.2.2:8080";

async function fetchStudentProducts() {
  const response = await fetch(`${BASE_URL}/api/student/products`);

  if (!response.ok) {
    throw new Error("상품 목록 조회 실패");
  }

  return response.json();
}
```

### 응답 예시

```json
[
  {
    "pluCode": "8809962586346",
    "name": "대정)참치마요삼각김밥",
    "category": "주먹밥"
  },
  {
    "pluCode": "8809962583475",
    "name": "대정)치킨마요삼각김밥",
    "category": "주먹밥"
  }
]
```

### 앱 처리 방식

| 필드 | 용도 |
|---|---|
| `name` | 앱 화면에 표시할 상품명 |
| `category` | 필요 시 화면에 표시할 분류 |
| `pluCode` | 신청 저장 시 백엔드로 보낼 상품 식별자 |

주의:

- 앱 화면에는 보통 `name`만 보여주면 됩니다.
- 신청할 때 상품명 문자열을 보내지 말고 반드시 `pluCode`를 보내야 합니다.
- `salesDate`는 앱에서 보낼 필요 없습니다. 백엔드가 최신 `daily_sales` 날짜를 자동으로 사용합니다.

## 2. 학생 상품 신청 저장

학생이 선택한 상품과 수량을 백엔드에 저장합니다.

```http
POST /api/student/requests
Content-Type: application/json
```

### 요청 예시

```json
{
  "studentId": "20240001",
  "items": [
    {
      "pluCode": "8809962586346",
      "quantity": 2
    },
    {
      "pluCode": "8809962583475",
      "quantity": 1
    }
  ]
}
```

### React Native 예시

```js
async function submitStudentRequest({ studentId, selectedItems }) {
  const response = await fetch(`${BASE_URL}/api/student/requests`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      studentId,
      items: selectedItems.map((item) => ({
        pluCode: item.pluCode,
        quantity: item.quantity,
      })),
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || "신청 저장 실패");
  }

  return response.json();
}
```

### 성공 응답 예시

```json
{
  "studentId": "20240001",
  "salesDate": "2026-04-24",
  "itemCount": 2,
  "totalQuantity": 3,
  "message": "학생 상품 신청이 저장되었습니다."
}
```

### 요청 검증 규칙

| 항목 | 규칙 |
|---|---|
| `studentId` | 필수, 빈 문자열 불가 |
| `items` | 최소 1개 이상 |
| `items[].pluCode` | 필수, 상품 목록 API에서 받은 값을 사용 |
| `items[].quantity` | 필수, 1 이상 |

주의:

- 같은 학생이 같은 상품을 다시 신청하면 기존 신청 수량이 갱신됩니다.
- 한 번의 요청 안에 같은 `pluCode`가 중복되면 실패합니다.
- 백엔드는 `pluCode`가 실제 상품인지, 신청 가능한 상품인지 검증합니다.

## 3. 대시보드 신청 현황 조회

대시보드에서 학생 신청 내역을 표시할 때 사용합니다.

```http
GET /api/student/requests
```

옵션:

```http
GET /api/student/requests?limit=100
```

### 응답 예시

```json
[
  {
    "studentId": "20240001",
    "productName": "대정)참치마요삼각김밥",
    "quantity": 2,
    "requestedAt": "2026-05-06T17:10:35.123"
  }
]
```

### 대시보드 표시 필드

| 필드 | 화면 표시 |
|---|---|
| `studentId` | 학생 아이디 |
| `productName` | 상품 이름 |
| `quantity` | 원하는 수량 |
| `requestedAt` | 신청 날짜/시간 |

## 앱 개발자 요약

```txt
GET /api/student/products로 상품 목록을 받아 name을 화면에 보여줍니다.
사용자가 수량을 선택하면 해당 상품의 pluCode와 quantity를 POST /api/student/requests로 보냅니다.
상품명은 요청에 보내지 않습니다. 백엔드가 pluCode로 상품명을 찾아 대시보드용 조회 API에 내려줍니다.
```
