<template>
  <div v-if="!isLoading" class="dashboard-container">
    <div class="dashboard-header">
      <div class="dashboard-header-heading">
        <h1>{{ $t('montage-all-campaigns') }}</h1>
      </div>
      <p class="dashboard-info">
        {{ $t('montage-manage-all') }}, {{ $t('montage-or') }}
        <RouterLink to="/">{{ $t('montage-view-active') }}</RouterLink>
      </p>
    </div>
    <section class="juror-campaigns" v-if="jurorCampaigns.length > 0">
      <h2>{{ $t('montage-juror-campaigns') }}</h2>
      <juror-campaign-card
        v-for="(campaign, index) in jurorCampaigns"
        :key="index"
        :campaign="campaign"
      />
    </section>
    <section class="coordinator-campaigns">
      <h2>{{ $t('montage-coordinator-campaigns') }}</h2>
      <div class="coordinator-campaign-cards">
        <coordinator-campaign-card
          v-for="(campaign, index) in coordinatorCampaigns"
          :key="index"
          :campaign="campaign"
        />
      </div>
    </section>
  </div>
  <clip-loader v-else size="80px" style="padding-top: 120px;" />
</template>

<script setup>
import { ref, onMounted } from 'vue'
import _ from 'lodash';

import adminService from '@/services/adminService'
import jurorService from '@/services/jurorService'
import alertService from '@/services/alertService';

// Components
import { RouterLink } from 'vue-router'
import CoordinatorCampaignCard from '@/components/Campaign/CoordinatorCampaignCard.vue'
import JurorCampaignCard from '@/components/Campaign/JurorCampaignCard.vue'


// State
const isLoading = ref(false)
const coordinatorCampaigns = ref([])
const jurorCampaigns = ref([])

onMounted(() => {
  isLoading.value = true

  // Fetch all campaigns
  const fetchCoordinatorCampaigns =  adminService
    .allCampaigns()
    .then((response) => {
      coordinatorCampaigns.value = response.data

      // Order campaigns by open date (more recent at the top)
      coordinatorCampaigns.value.sort((campaign1, campaign2) => {
        if (campaign1.open_date === campaign2.open_date) {
          return 0
        } else if (campaign1.open_date < campaign2.open_date) {
          return 1
        } else {
          return -1
        }
      })
    })
    .catch(alertService.error)

  // Fetch all juror campaigns
  const fetchJurorCampaigns = jurorService
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

      let campaignsJuror = _.values(roundsGroupedByCampaigns)

      // Order campaigns by open date (more recent at the top)
      campaignsJuror.sort((campaign1, campaign2) => {
        const getOpenDate = (campaign) =>
          campaign.length > 0 && campaign[0].campaign ? campaign[0].campaign.open_date : null

        const campaign1OpenDate = getOpenDate(campaign1)
        const campaign2OpenDate = getOpenDate(campaign2)

        if (campaign1OpenDate === campaign2OpenDate) {
          return 0
        } else if (campaign1OpenDate < campaign2OpenDate) {
          return 1
        } else {
          return -1
        }
      })

      jurorCampaigns.value = campaignsJuror
    })
    .catch(alertService.error)

    Promise.all([fetchCoordinatorCampaigns, fetchJurorCampaigns]).finally(() => {
    isLoading.value = false
  })
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
