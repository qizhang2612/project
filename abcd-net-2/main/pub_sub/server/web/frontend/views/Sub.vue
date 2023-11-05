<template>
    <a-layout>
    <a-layout-content
        :style="{ background: '#fff', padding: '100px', margin: 0, minHeight: '550px' }"
    >
        <a-table :columns="columns" :data-source="hosts">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'host_name'">
              <a>
                {{ record.host_name }}
              </a>
            </template>
            <template v-else-if="column.key === 'type'">
              <a>
                {{ record.type }}
              </a>
            </template>
            <template v-else-if="column.key === 'location'">
              <a>
                {{ record.location }}
              </a>
            </template>
            <template v-else-if="column.key === 'description'">
              <a>
                {{ record.description }}
              </a>
            </template>
            <template v-else-if="column.key === 'ip'">
              <a>
                {{ record.ip }}
              </a>
            </template>
          </template>
  </a-table>

    </a-layout-content>
  </a-layout>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import axios from 'axios';
import { ref, onMounted } from 'vue';

const columns = [
  {
    title: "名称",
    dataIndex: 'host_name',
    key: 'host_name',
  },
  {
    title: '类型',
    key: 'type',
    dataIndex: 'type',
  },
  {
    title: '位置',
    key: 'location',
    dataIndex: 'location',
  },
  {
    title: '描述',
    key: 'description',
    dataIndex: 'description',
  },
  {
    title: 'IP',
    key: 'ip',
    dataIndex: 'ip',
  },

];

export default defineComponent({
  components: {
  },
  setup() {
    const hosts = ref()

    const handleQuery = () => {
      axios.get("/v1/hosts", {
       params: {
       }
      }).then((response) => {
        const data = response.data
        hosts.value = data.msg
        console.log(hosts.value)
      });
    };

    onMounted(() => {
          setInterval(() => {
          handleQuery()
        }, 200)
    });

    return {
      handleQuery,
      hosts,
      columns,
    };
  },
});
</script>

