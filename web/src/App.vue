#template
<template>
  <div id="app" class="app">
    <div class="card">
      <h1>个人知识库</h1>
      <Register />
    </div>
  </div>
</template>

<script setup>
import Register from './components/Register.vue'
</script>
<style>
html, body, #app { height: 100%; margin: 0; }
#app.app {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ff8c42;
  font-family: Arial, Helvetica, sans-serif;
}
.card {
  background: #ffffff;
  padding: 24px;
  border-radius: 12px;
  width: 380px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  text-align: center;
}
.card h1 { margin: 0 0 14px; font-size: 20px; color: #333; }
form { display: flex; flex-direction: column; gap: 12px; }
.input {
  padding: 10px 12px;
  border-radius: 10px;
  border: none;
  background: #ffffff;
  box-shadow: inset 0 0 0 1px rgba(0,0,0,0.06);
  font-size: 14px;
}
.btn {
  padding: 10px 12px;
  border-radius: 10px;
  border: none;
  background: #ff8c42;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}
.message { margin-top: 8px; color: #d9534f; }
</style>
