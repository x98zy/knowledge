<template>
  <div class="auth-page">
    <div class="deco deco-book1">📘</div>
    <div class="deco deco-book2">📖</div>
    <div class="deco deco-book3">✏️</div>
    <div class="deco-grid"></div>

    <div class="card-wrapper">
      <div class="glass-card">
        <div class="card-brand">
          <span class="brand-icon">📚</span>
          <h1>个人知识库</h1>
        </div>
        <form class="panel-form" @submit.prevent="onSubmit">
          <h2 class="panel-title">注册</h2>
          <p class="panel-subtitle">创建你的知识库账号</p>

          <div class="field">
            <input
              v-model="username"
              class="field-input"
              type="text"
              placeholder="用户名（3-50 字符）"
              required
            />
            <span class="field-error" v-if="errors.username">{{ errors.username }}</span>
          </div>

          <div class="field">
            <input
              v-model="email"
              class="field-input"
              type="email"
              placeholder="邮箱"
              required
            />
            <span class="field-error" v-if="errors.email">{{ errors.email }}</span>
          </div>

          <div class="field">
            <input
              v-model="password"
              class="field-input"
              type="password"
              placeholder="密码（至少 8 位，含大小写、数字、特殊字符）"
              required
            />
            <span class="field-error" v-if="errors.password">{{ errors.password }}</span>
          </div>

          <div class="field">
            <input
              v-model="confirm_password"
              class="field-input"
              type="password"
              placeholder="确认密码"
              required
            />
            <span class="field-error" v-if="errors.confirm_password">{{ errors.confirm_password }}</span>
          </div>

          <button class="btn" type="submit" :disabled="loading">
            {{ loading ? '注册中...' : '注册' }}
          </button>

          <p class="message error" v-if="apiError">{{ apiError }}</p>
          <p class="message success" v-if="success">{{ success }}</p>

          <p class="switch-link">
            已有账号？
            <a href="#" @click.prevent="$router.push('/login')">立即登录</a>
          </p>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { register } from '../api'

const router = useRouter()

const username = ref('')
const email = ref('')
const password = ref('')
const confirm_password = ref('')
const loading = ref(false)
const apiError = ref('')
const success = ref('')
const errors = reactive({ username: '', email: '', password: '', confirm_password: '' })

function validate() {
  let valid = true
  errors.username = ''
  errors.email = ''
  errors.password = ''
  errors.confirm_password = ''

  if (username.value.length < 3) {
    errors.username = '用户名长度至少 3 个字符'
    valid = false
  }

  const emailRe = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
  if (!emailRe.test(email.value)) {
    errors.email = '邮箱格式不正确'
    valid = false
  }

  const pw = password.value
  if (pw.length < 8) {
    errors.password = '密码长度至少 8 位'
    valid = false
  } else if (!/[A-Z]/.test(pw) || !/[a-z]/.test(pw) || !/\d/.test(pw) || !/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?~`]/.test(pw)) {
    errors.password = '密码必须包含大写字母、小写字母、数字和特殊字符'
    valid = false
  }

  if (password.value !== confirm_password.value) {
    errors.confirm_password = '两次输入的密码不一致'
    valid = false
  }

  return valid
}

const onSubmit = async () => {
  apiError.value = ''
  success.value = ''

  if (!validate()) return

  loading.value = true
  try {
    await register({
      username: username.value,
      email: email.value,
      password: password.value,
      confirm_password: confirm_password.value,
    })
    success.value = '注册成功！即将跳转到登录页...'
    setTimeout(() => router.push('/login'), 1500)
  } catch (e) {
    if (e.response?.data?.message) {
      apiError.value = e.response.data.message
    } else {
      apiError.value = '网络异常，请稍后重试'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
*,
*::before,
*::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
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

.card-wrapper {
  width: 420px;
  min-height: 520px;
  position: relative;
  z-index: 1;
}

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
</style>
