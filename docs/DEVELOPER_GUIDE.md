# Montage Developer Architecture Guide

This guide outlines the architectural patterns and best practices established during the GSoC 2026 hardening phase. These patterns ensure Montage remains scalable, maintainable, and robust.

## 1. Defensive Service Layer (Axios Interceptors)

The frontend communicates with the backend via a centralized Service Layer (`frontend/src/services/api.js`). We have implemented a global interceptor pattern that handles:

- **Unified Error Handling**: Automatically catches non-200 responses and standardizes error reporting via `alertService`.
- **Global Loading State**: Manages the `loadingStore` to provide consistent UI feedback.
- **Runtime Schema Validation**: In development mode, the interceptor validates incoming data against expected schemas to catch API regressions early.

### Example: Runtime Validation
```javascript
if (response.config.url.includes('/campaign/')) {
  validateSchema(res.data, { id: 'number', name: 'string' }, 'Campaign');
}
```

## 2. Asynchronous Form Intelligence

To improve UX and reduce server-side load from invalid submissions, we use asynchronous field validation.
- **Debounced Checks**: Inputs like Campaign Name are validated against the backend in real-time with a debounce delay.
- **Zod Schema Integration**: All forms use Zod for complex client-side constraints (date ranges, URL formatting) before submission.

## 3. Multi-Media Pipeline

Montage has been transformed from an image-viewer to a media-agnostic platform.
- **`CommonsMedia.vue`**: A polymorphic component that handles `image`, `audio`, and `video` types based on MIME major type.
- **Metadata Extraction**: The backend `loaders.py` extracts EXIF data (like Camera Model) to provide jurors with crucial context without leaving the app.

## 4. UI/UX Principles

- **Layout Stability**: We prioritize layout stability by keeping headers visible during loads and using **Skeleton Loaders** for content areas.
- **State Persistence**: User preferences (like Grid Size) are persisted in `localStorage` to ensure a seamless experience across sessions.

---
*Maintained by the GSoC 2026 Selection Taskforce.*
