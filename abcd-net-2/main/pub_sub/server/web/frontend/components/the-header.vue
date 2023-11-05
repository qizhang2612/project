<template>
  <a-layout-header class="header">
    <div class="logo" />
    <a-menu
        theme="dark"
        mode="horizontal"
        v-model:selectedKeys="selectedKeys1"
        :style="{ lineHeight: '64px' }"
    >
      <a-menu-item key="1">
        <router-link to="/">发布订阅状态</router-link>
      </a-menu-item>

      <a-menu-item key="2">
        <router-link to="/sub">订阅端</router-link>
      </a-menu-item>

    </a-menu>
  </a-layout-header>
</template>

<script>
export default {
  name: "the-header"
}
</script>

<style scoped>

</style>

