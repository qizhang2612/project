<template>
    <a-layout>
    <a-layout-content
        :style="{ background: '#fff', padding: '100px', margin: 0, minHeight: '550px' }"
    >
        <a-table :columns="columns" :data-source="relations">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'topic'">
              <a>
                {{ record.topic }}
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
            <template v-else-if="column.key === 'sub'">
              <span>
                <a-tag
                  v-for="sub in record.sub"
                  :key="sub"
                  :color="'green'"
                >
                  {{ sub }}
                </a-tag>
              </span>
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
    title: "主题",
    dataIndex: 'topic',
    key: 'topic',
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
  {
    title: '订阅者',
    key: 'sub',
    dataIndex: 'sub',
  },
];

export default defineComponent({
  components: {
  },
  setup() {
    const relations = ref()

    const handleQuery = () => {
      axios.get("/v1/relations", {
       params: {
       }
      }).then((response) => {
        const data = response.data
        relations.value = data.msg
        console.log(relations.value)
      });
    };

    onMounted(() => {
          setInterval(() => {
          handleQuery()
        }, 200)
    });

    return {
      handleQuery,
      relations,
      columns,
    };
  },
});
</script>

