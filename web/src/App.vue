<script setup>
import { ref, shallowRef } from 'vue'
import Login from './components/Login.vue'
import Register from './components/Register.vue'

const currentPanel = shallowRef('login')

function showRegister() {
  currentPanel.value = 'register'
}

function showLogin() {
  currentPanel.value = 'login'
}
</script>

<template>
  <div class="auth-page">
    <div class="deco deco-book1">&#128218;</div>
    <div class="deco deco-book2">&#128214;</div>
    <div class="deco deco-book3">&#9997;</div>
    <div class="deco-grid"></div>

    <div class="card-wrapper">
      <Transition name="flip" mode="out-in">
        <!-- Login panel -->
        <div v-if="currentPanel === 'login'" key="login" class="glass-card">
          <div class="card-brand">
            <span class="brand-icon">&#128218;</span>
            <h1>知识库</h1>
          </div>
          <Login @switch="showRegister" />
        </div>

        <!-- Register panel -->
        <div v-else key="register" class="glass-card">
          <div class="card-brand">
            <span class="brand-icon">&#128218;</span>
            <h1>知识库</h1>
          </div>
          <Register @switch="showLogin" />
        </div>
      </Transition>
    </div>
  </div>
</template>

<style>
*,
*::before,
*::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html,
body {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
  position: relative;
  overflow: hidden;
}

.deco-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 60px 60px;
  pointer-events: none;
}

.deco {
  position: absolute;
  font-size: 48px;
  opacity: 0.08;
  pointer-events: none;
  animation: float 6s ease-in-out infinite;
}

.deco-book1 { top: 10%; left: 8%; animation-delay: 0s; }
.deco-book2 { top: 60%; right: 10%; animation-delay: 2s; }
.deco-book3 { bottom: 15%; left: 15%; animation-delay: 4s; }

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-20px); }
}

/* Card wrapper */
.card-wrapper {
  width: 420px;
  min-height: 520px;
  perspective: 1200px;
  position: relative;
  z-index: 1;
}

/* Flip transition */
.flip-enter-active,
.flip-leave-active {
  transition: transform 0.5s ease-in-out, opacity 0.3s ease;
  transform-origin: center center;
}

.flip-leave-active {
  position: absolute;
  width: 100%;
}

.flip-enter-from {
  transform: rotateY(-90deg);
  opacity: 0;
}

.flip-leave-to {
  transform: rotateY(90deg);
  opacity: 0;
}

.flip-enter-to {
  transform: rotateY(0);
  opacity: 1;
}

.flip-leave-from {
  transform: rotateY(0);
  opacity: 1;
}

/* Glassmorphism card */
.glass-card {
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 20px;
  padding: 40px 36px;
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.1);
}

.card-brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 28px;
}

.brand-icon { font-size: 32px; }

.card-brand h1 {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 1px;
}

.panel-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.panel-title {
  font-size: 20px;
  font-weight: 600;
  color: #fff;
  text-align: center;
}

.panel-subtitle {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.55);
  text-align: center;
  margin-top: -8px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-input {
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.field-input::placeholder {
  color: rgba(255, 255, 255, 0.35);
}

.field-input:focus {
  border-color: #2d8cf0;
  box-shadow: 0 0 0 3px rgba(45, 140, 240, 0.2);
}

.field-error {
  font-size: 11px;
  color: #ff6b6b;
  padding-left: 4px;
}

.btn {
  padding: 13px;
  border-radius: 12px;
  border: none;
  background: linear-gradient(135deg, #2d8cf0, #1a5fb4);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.2s;
  letter-spacing: 0.5px;
}

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(45, 140, 240, 0.4);
}

.btn:active:not(:disabled) {
  transform: translateY(0);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.message {
  text-align: center;
  font-size: 13px;
  padding: 8px 12px;
  border-radius: 8px;
}

.message.error {
  color: #ff6b6b;
  background: rgba(255, 107, 107, 0.1);
}

.message.success {
  color: #51cf66;
  background: rgba(81, 207, 102, 0.1);
}

.switch-link {
  text-align: center;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  margin-top: 4px;
}

.switch-link a {
  color: #2d8cf0;
  text-decoration: none;
  font-weight: 600;
}

.switch-link a:hover {
  text-decoration: underline;
}

@media (prefers-reduced-motion: reduce) {
  .flip-enter-active,
  .flip-leave-active {
    transition: none;
  }
  .deco {
    animation: none;
  }
}
</style>
