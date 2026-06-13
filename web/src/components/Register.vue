<template>
  <form @submit.prevent="onSubmit">
    <input class="input" placeholder="用户名" v-model="username" required />
    <input class="input" type="password" placeholder="密码" v-model="password" required />
    <input class="input" type="password" placeholder="确认密码" v-model="re_password" required />
    <button class="btn" type="submit">注册</button>
    <p class="message" v-if="message">{{ message }}</p>
  </form>
</template>

<script setup>
import { ref } from 'vue'
import api from '../api'

const username = ref('')
const password = ref('')
const re_password = ref('')
const message = ref('')

const onSubmit = async () => {
  try {
    const res = await api.post('/user', {
      username: username.value,
      password: password.value,
      re_password: re_password.value
    })
    message.value = res.data.message || '注册成功'
  } catch (e) {
    if (e.response && e.response.data && e.response.data.message) {
      message.value = e.response.data.message
    } else {
      message.value = '请求失败'
    }
  }
}
</script>
