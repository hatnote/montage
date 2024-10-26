<template>
  <div class="dashboard-container">
    <div class="dashboard-header">
      <div class="dashboard-header-heading">
        <h1>All Campaigns</h1>
      </div>
      <p class="dashboard-info">
        View all campaigns, active and archived below, or
        <RouterLink to="/">view only active campaigns and rounds.</RouterLink>
      </p>
    </div>

    <section class="coordinator-campaigns">
      <h2>Coordinator Campaigns</h2>
      <div class="coordinator-campaign-cards">
        <coordinator-campaign-card
          v-for="(campaign, index) in coordinatorCampaigns"
          :key="index"
          :campaign="campaign"
        />
      </div>
    </section>

    <section class="juror-campaigns" v-if="jurorCampaigns.length > 0">
      <h2>Juror Campaigns</h2>
      <juror-campaign-card
        v-for="(campaign, index) in jurorCampaigns"
        :key="index"
        :campaign="campaign"
      />
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import _ from 'lodash';

import adminService from '@/services/adminService'
import jurorService from '@/services/jurorService'
import alertService from '@/services/alertService';

import { RouterLink } from 'vue-router'
import CoordinatorCampaignCard from '@/components/Campaign/CoordinatorCampaignCard.vue'
import JurorCampaignCard from '@/components/Campaign/JurorCampaignCard.vue'


const coordinatorCampaigns = ref([])
const jurorCampaigns = ref([])

onMounted(() => {
  // Fetch all campaigns
  adminService
    .allCampaigns()
    .then((response) => {
      coordinatorCampaigns.value = response.data
    })
    .catch(alertService.error)

  // Fetch all juror campaigns
  jurorService
    .allCampaigns()
    .then((response) => {
      if (!response.data.length) {
        jurorCampaigns.value = [];
        return;
      }

      const roundsGroupedByCampaigns = _.groupBy(
        response.data.filter((round) => round.status !== 'cancelled'),
        'campaign.id'
      );

      jurorCampaigns.value = _.values(roundsGroupedByCampaigns);
    })
    .catch(alertService.error)
})
</script>

<style scoped>
.dashboard-container {
  padding: 40px;
}

.dashboard-header {
  margin-bottom: 32px;
}

.dashboard-header-heading {
  display: flex;
  justify-content: space-between;
}

.dashboard-info {
  margin-top: 8px;
  font-size: 14px;
  color: #666;
}

.dashboard-link {
  color: #006cb6;
  text-decoration: none;
}

.dashboard-link:hover {
  text-decoration: underline;
}

.coordinator-campaigns {
  margin-bottom: 40px;
}

.coordinator-campaigns h2 {
  margin-bottom: 16px;
}

.coordinator-campaign-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.juror-campaigns {
  margin-top: 40px;
}
</style>
