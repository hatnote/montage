<template>
  <footer class="footer-container">
    <div class="footer-left">
      <span>&copy; 2024 // by Montage team</span>
      <a
        href="https://commons.wikimedia.org/wiki/Commons:Montage"
        class="footer-link"
        target="_blank"
        >About Montage</a
      >
      <a href="https://github.com/hatnote/montage" class="footer-link" target="_blank">
        Source code
      </a>
    </div>
    <div class="footer-right">
      <span class="env-label">DEV</span>
    </div>
  </footer>
</template>

<style scoped>
.footer-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  font-size: 14px;
  color: #666;
  border-top: 1px solid #e0e0e0;
}

.footer-left {
  display: flex;
  align-items: center;
}

.footer-link {
  margin-left: 12px;
  color: #006cb6;
  text-decoration: none;
}

.footer-link:hover {
  text-decoration: underline;
}

.env-label {
  font-weight: bold;
  color: #006cb6;
}
</style>
