# ADR-001: Đặt frontend ở đâu? (Firebase / Vercel / Cloudflare Pages / cùng container)

- **Trạng thái:** ✅ **ĐÃ CHỐT — Phương án D (Cloudflare Pages).** PO quyết định 2026-10-15, cùng với backend trên Google Cloud Run.
- **Ngày:** 2026-10-15 (bản 2 — mở rộng thành 4 phương án)
- **Liên quan:** §5.2, §9.3 và Q1 trong [KE-HOACH-NANG-CAP-CI-CD-2-TUAN.md](KE-HOACH-NANG-CAP-CI-CD-2-TUAN.md)

---

## 1. Bối cảnh

Backend chạy trên **Cloud Run với `min-instances = 0`** — ràng buộc **bắt buộc** để giữ chi phí $0. Hệ quả: container **ngủ khi không có traffic** và **phải khởi động lại ở request đầu** (cold start).

Frontend chỉ là **một trang tĩnh**: chọn/chụp ảnh → gửi lên `/predict` → hiển thị kết quả.

**Bốn phương án:**

| | Phương án | Frontend phục vụ bởi | Số deploy target |
|---|---|---|---|
| **A** | **Firebase Hosting** | CDN Firebase | 2 |
| **B** | **Cùng container Cloud Run** | Chính container FastAPI | **1** |
| **C** | **Vercel** | Edge network Vercel | 2 |
| **D** | **Cloudflare Pages** | CDN Cloudflare | 2 |

---

## 2. Dữ kiện — và mức độ tin cậy

> ⚠️ **Minh bạch về nguồn:** trong phiên này tôi **chỉ tải được đầy đủ tài liệu Cloudflare**. Tài liệu Vercel và Hugging Face render bằng JS nên bị cắt, tôi **không xác minh được**. Các ô ⚠️ **phải kiểm tra lại**.

| Tiêu chí | Firebase | Vercel (Hobby) | **Cloudflare Pages (Free)** |
|---|---|---|---|
| Băng thông miễn phí | 360 MB/ngày (~10,8 GB/tháng) | ⚠️ ~100 GB/tháng | ✅ **Tài liệu limits không ghi giới hạn băng thông** |
| Số build miễn phí | Qua CLI/CI | ⚠️ chưa xác minh | ✅ **500 build/tháng**, 1 build đồng thời, timeout 20 phút |
| Preview deploy mỗi PR | Có *preview channels*, **phải tự nối vào CI** | ✅ Nổi tiếng nhất | ✅ **Không giới hạn số preview** |
| Tên miền riêng + SSL | ✅ | ✅ | ✅ **tới 100 tên miền/dự án** |
| Giới hạn file | — | — | 20.000 file, **tối đa 25 MiB/file** |
| Hạn chế dùng thương mại ở gói free | Không | ⚠️ Hobby **thường bị giới hạn phi thương mại** | ✅ Không |
| Rollback | Có | Có | ✅ Có (tài liệu riêng) |

**Nguồn đã kiểm chứng:** [Cloudflare Pages — Limits](https://developers.cloudflare.com/pages/platform/limits/) và [Cloudflare Pages — Redirects](https://developers.cloudflare.com/pages/configuration/redirects/).

---

## 3. ⚠️ ĐÍNH CHÍNH: tôi đã suýt tư vấn sai về Cloudflare

Ở bản 1 của ADR này, tôi đề xuất phương án "tốt nhất cả hai": dùng **proxy** để trang tĩnh phục vụ từ CDN nhưng API đi **cùng origin** (hết CORS, hết cold start khi mở trang).

Với Cloudflare Pages, tôi đã giả định có thể làm điều đó bằng một dòng trong `_redirects`:

```
/api/*  https://my-service.run.app/api/:splat  200
```

**Điều này KHÔNG hoạt động.** Tài liệu Cloudflare nói rõ:

> *"Proxying will only support relative URLs on your site. **You cannot proxy external domains.**"*

⇒ **`_redirects` của Cloudflare Pages không thể trỏ ra Cloud Run.** Đây là điểm tôi đã hiểu sai và cần ghi lại để nhóm không mất thời gian thử.

**Cách làm đúng trên Cloudflare:** phải dùng **Pages Functions** (một Worker nhỏ) tự `fetch()` sang Cloud Run:

```js
// functions/api/[[path]].js
export async function onRequest(context) {
  const url = new URL(context.request.url);
  const target = "https://<service>.run.app" + url.pathname + url.search;
  return fetch(target, {
    method: context.request.method,
    headers: context.request.headers,
    body: context.request.body,
  });
}
```

Chạy được, nhưng **tốn quota Workers** (⚠️ free ~100.000 request/ngày) và thêm code phải bảo trì.

**Với Vercel:** `rewrites` trong `vercel.json` **có** hỗ trợ URL bên ngoài, nên phương án proxy khả thi hơn — ⚠️ nhưng tôi **không xác minh được** trong phiên này.

---

## 4. Phân tích theo tiêu chí

### 4.1. ⭐ Cold start ảnh hưởng tới *trang web*, không chỉ API

**Phương án B (cùng container):** HTML/CSS/JS nằm trong container ⇒ người dùng mở link phải **chờ container khởi động trước khi có bất kỳ thứ gì để hiển thị**.

```
Mở link → container đang ngủ → 5–20 giây TRANG TRẮNG → trang hiện ra
```

Với `min-instances=0` và lưu lượng thấp kiểu demo/bảo vệ đồ án, **gần như mọi lượt truy cập đều cold** — đây là khuyết điểm **lặp lại**, không phải sự cố một lần.

**Phương án A / C / D:** trang tĩnh tải **tức thì** từ CDN. Cold start chỉ xảy ra khi bấm "Dự đoán" — lúc đó đã có giao diện và spinner.

> **Kết luận: B bị loại ở tiêu chí này; A, C, D ngang nhau.**

### 4.2. ⭐ Rủi ro lệch phiên bản (version skew)

**A / C / D:** frontend và backend deploy **độc lập** ⇒ có thể lệch. Ví dụ: frontend mới đọc `status: "no_hand"` nhưng backend cũ trả `{"letter": null}` ⇒ giao diện hiển thị sai, và **lỗi chỉ xuất hiện sau khi deploy một nửa**.

**B:** một artifact duy nhất ⇒ **không thể lệch**.

> **Kết luận: B thắng.** Đây là lợi thế thật, cần cân nhắc nghiêm túc.
> **Biện pháp:** cố định hợp đồng API trong 2 tuần + **deploy backend trước, frontend sau**.

### 4.3. Preview deployment mỗi Pull Request — giá trị học CI/CD cao nhất

Đây là tính năng tôi đánh giá **cao nhất về mặt học tập**, và là lý do chính khiến C/D hơn A:

- Mỗi PR được deploy ra **một URL riêng** để cả nhóm bấm vào thử **trước khi merge**.
- Biến review từ "đọc diff" thành "dùng thử sản phẩm".
- Dạy được khái niệm **môi trường tạm** — thứ mà pipeline một-môi-trường không dạy được.

✅ **Cloudflare Pages: không giới hạn số preview deployment** (đã xác minh).
✅ **Vercel:** preview deployment là tính năng nổi tiếng nhất của họ.
⚠️ **Firebase:** có *preview channels*, nhưng **phải tự nối vào CI**, không tự động như hai bên kia.

> **Kết luận: C và D thắng A rõ rệt.**

### 4.4. CORS và độ phức tạp cấu hình

| | A / C / D | B |
|---|---|---|
| CORS | Phải bật `CORSMiddleware` + xử lý preflight | **Không tồn tại** |
| Công sức | ~30 phút | 0 |

> **Kết luận: B thắng**, nhưng đây là chi phí **một lần**, không phải rủi ro kéo dài. Không nên để tiêu chí này chi phối.

### 4.5. Chi phí

- **D (Cloudflare):** mạnh nhất — tài liệu limits **không ghi giới hạn băng thông**, 500 build/tháng.
- **C (Vercel):** ⚠️ ~100 GB/tháng — thừa sức cho demo.
- **A (Firebase):** yếu nhất — **360 MB/ngày** ≈ ~1.800 lượt tải trang/ngày. Đủ cho demo nhưng là mức thấp nhất trong ba.

> **Kết luận: D > C > A.**

### 4.6. Sử dụng nhân lực (4 người)

A/C/D đều cho P2 việc thật: trang tĩnh + pipeline riêng + CORS. **B** thì P2 gần như hết việc sau Ngày 2.

> **Kết luận: A/C/D thắng.**

### 4.7. Gỡ lỗi, chạy local

**B** đơn giản nhất: một lệnh `docker run`, một nguồn log. A/C/D cần thêm một static server khi chạy local và có nhiều tầng hơn khi gỡ lỗi.

> **Kết luận: B thắng.** Với nhóm lần đầu làm cloud, ít bộ phận chuyển động = ít khả năng trễ hạn.

### 4.8. Tên miền, HTTPS, độ trễ

| | Firebase | Vercel | Cloudflare |
|---|---|---|---|
| HTTPS mặc định | ✅ `*.web.app` | ✅ `*.vercel.app` | ✅ `*.pages.dev` |
| Tên miền riêng | ✅ miễn phí | ✅ miễn phí | ✅ miễn phí |
| Hiện diện edge tại VN | — | ⚠️ | Cloudflare có PoP tại VN (mức độ ảnh hưởng nhỏ) |

---

## 5. Tổng hợp

| Tiêu chí | Trọng số | A Firebase | B Cùng container | C Vercel | D Cloudflare |
|---|---|---|---|---|---|
| Cold start khi mở trang | **Cao** | ✅✅ | ❌❌ | ✅✅ | ✅✅ |
| Preview deploy mỗi PR | **Cao** | ⚠️ | ❌ | ✅✅ | ✅✅ |
| Giá trị học CI/CD | **Cao** | ✅ | ❌ | ✅✅ | ✅✅ |
| Lệch phiên bản | **Cao** | ❌ | ✅✅ | ❌ | ❌ |
| Băng thông free | Trung bình | ❌ | n/a | ✅ | ✅✅ |
| Sử dụng nhân lực | Trung bình | ✅✅ | ❌ | ✅✅ | ✅✅ |
| CORS | Thấp–TB | ❌ | ✅✅ | ❌ | ❌ |
| Gỡ lỗi, chạy local | Trung bình | ❌ | ✅✅ | ❌ | ❌ |
| Proxy ra Cloud Run | Thấp | ⚠️ | n/a | ✅ | ❌ *(phải dùng Functions)* |

---

## 6. Quyết định đề xuất

> ### Chọn **D — Cloudflare Pages**, với **C — Vercel** là phương án thay thế tương đương.
>
> **Cả hai đều tốt hơn Firebase (A)** cho dự án này.

**Lý do chọn D:**
1. **Băng thông không thấy giới hạn** trong tài liệu limits — mức hào phóng nhất trong ba.
2. **Preview deployment không giới hạn** — tính năng học CI/CD giá trị nhất (§4.3).
3. **Không hạn chế dùng thương mại** ở gói free (Vercel Hobby ⚠️ thường có).
4. **Tôi xác minh được số liệu** từ tài liệu chính thức — ba phương án kia thì không.

**Lý do C ngang hàng:** Vercel có DX tốt nhất và preview deployment bóng bẩy nhất. Nếu nhóm thấy Vercel dễ dùng hơn thì **chọn C không sai** — khác biệt giữa C và D nhỏ hơn nhiều so với khác biệt giữa chúng và A/B.

**Vì sao không chọn A (Firebase):** băng thông thấp nhất (360 MB/ngày) và preview deployment phải tự nối vào CI. Không có lý do gì để chọn A khi C và D đều miễn phí và tốt hơn.

### Biện pháp giảm thiểu (bắt buộc)

**MT-1 — Warm-up ping khi tải trang.** Quan trọng nhất, và **chỉ làm được ở A/C/D**:

```js
// Chạy ngay khi trang tải xong, KHÔNG chờ người dùng bấm gì
fetch(`${API_BASE}/health`).catch(() => {});
```

Container khởi động **ngay lúc trang hiện ra**, trong khi người dùng còn chọn ảnh ⇒ tới lúc bấm "Dự đoán", container **đã ấm** ⇒ **cold start gần như bị triệt tiêu về cảm nhận**.

> Đây là lý do cốt lõi khiến A/C/D thắng B: ở B, **không thể** phát warm-up ping vì chưa có trang để chạy nó.

**MT-2 — Cố định hợp đồng API.** Trong 2 tuần **không đổi hình dạng response**. Nếu buộc đổi, đặt version vào đường dẫn (`/v1/predict`). Đây là cách rẻ nhất vô hiệu hoá rủi ro lệch phiên bản.

**MT-3 — Deploy backend TRƯỚC, frontend SAU.** Backend luôn tương thích ngược; frontend là bên thích nghi.

**MT-4 — Deploy bằng GitHub Actions + CLI, KHÔNG dùng Git integration của nền tảng.**

```yaml
# Cloudflare: npx wrangler pages deploy web/ --project-name=...
# Vercel:     npx vercel deploy --prod --token=...
```

Lý do: mục tiêu của dự án là **học CI/CD**. Nếu để nền tảng tự động deploy khi push, **toàn bộ logic pipeline nằm trong hộp đen của họ** — nhóm không học được gì và không có chỗ để thêm bước test/approval. Đưa việc deploy vào GitHub Actions giữ **một nơi duy nhất** chứa toàn bộ quy trình.

---

## 7. Chi phí đảo ngược quyết định: RẤT THẤP

Đây là điểm để **không mất thời gian cân nhắc**: frontend chỉ là **một file tĩnh**. Chuyển giữa A ↔ C ↔ D ↔ B mất **khoảng 1 giờ**.

> **Quy tắc thực thi:** chọn **D (Cloudflare Pages)**, làm xong trong Ngày 2 và **không quay lại bàn lại**. Nếu tới **hết Ngày 5** nhóm trễ tiến độ, **chuyển sang B** (cùng container) — ít bộ phận chuyển động nhất, bảo vệ đường găng.

---

## 8. Điều gì sẽ khiến tôi đổi ý

| Nếu... | Thì chọn |
|---|---|
| Vercel `rewrites` ra URL ngoài chạy được ở Hobby **và** nhóm muốn hết CORS | **C** (Vercel) — được thêm lợi thế proxy |
| Nhóm trễ tiến độ tới hết Ngày 5 | **B** |
| Nhóm đã quen Firebase | **A** — nhưng đây là lựa chọn yếu nhất trong ba |
| Cold start ONNX đo được ≤ 2 giây | Cân nhắc lại **B** — khuyết điểm trang trắng bớt nghiêm trọng |
