<template>
  <a-layout>
    <the-header></the-header>
    <router-view/>
    <the-footer></the-footer>
  </a-layout>
</template>

<style>

</style>

<script>
import TheHeader from "./components/the-header";
import TheFooter from "./components/the-footer";
export default {
  components: {TheHeader, TheFooter}
}
</script>