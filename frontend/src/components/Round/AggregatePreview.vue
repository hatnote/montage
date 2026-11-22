<template>
	<div class="aggregate-preview">
		<cdx-card style="margin-top: 24px">
			<template #supporting-text>
				<div class="preview-header">
					<h3>
						{{ $t( 'Aggregate Preview Results' ) }}
						<span v-if="isCommitted" class="committed-badge"> Saved </span>
					</h3>
					<div class="preview-meta">
						<span>{{ $t( 'Total' ) }}: {{ result.total_entries }}</span>
						<span
							v-if="result.excluded_count > 0"
							class="excluded"
						>
							{{ result.excluded_count }}
							{{ $t( 'Aggregate Excluded' ) }}
						</span>
					</div>
				</div>

				<!-- Results Grid -->
				<div
					v-if="result.ranked && result.ranked.length"
					class="results-grid"
				>
					<div
						v-for="item in paginatedResults"
						:key="item.entry.id"
						class="result-card"
						:class="{ 'tied-card': isTied( item ) }"
					>
						<div class="image-wrapper">
							<img
								:src="`https://commons.wikimedia.org/wiki/Special:FilePath/${ encodeURIComponent( item.entry.name ) }`"
								:alt="item.entry.name"
							>
						</div>

						<div class="card-content">
							<div class="card-rank">
								#{{ item.rank + 1 }}
								<span
									v-if="isTied( item )"
									class="tie-badge"
								>
									tie
								</span>
							</div>

							<a
								class="image-link"
								:href="`https://commons.wikimedia.org/wiki/File:${ item.entry.name }`"
								target="_blank"
								rel="noopener"
							>
								{{ item.entry.name }}
							</a>

							<div class="score">
								{{ $t( 'Score' ) }}:
								<strong>{{ item.score.toFixed( 3 ) }}</strong>
							</div>
						</div>
					</div>
				</div>

				<div
					v-else
					class="empty-state"
				>
					{{ $t( 'No results' ) }}
				</div>

                <div
	                v-if="totalPages > 1"
	                class="pagination"
                >
	                <div class="pagination-info">
		                Showing {{ pageStart }}–{{ pageEnd }}
		                of {{ result.ranked.length }}
	                </div>

	                <div class="pagination-controls">
		                <cdx-button
			                action="default"
			                :disabled="currentPage === 1"
			                @click="currentPage--"
		                >
			                Previous
		                </cdx-button>

		                <span class="page-number">
			                Page {{ currentPage }} of {{ totalPages }}
		                </span>

		                <cdx-button
			                action="default"
			                :disabled="currentPage === totalPages"
			                @click="currentPage++"
		                >
			                Next
		                </cdx-button>
	                </div>
                </div>

				<div class="button-group">
					<cdx-button
						v-if="!isCommitted"
						action="progressive"
						weight="primary"
						:disabled="isLoading || !result.ranked || result.ranked.length === 0"
						@click="$emit( 'commit' )"
					>
						<check class="icon-small" />
						{{ $t( 'Aggregate commit' ) }}
					</cdx-button>

					<cdx-button
						action="default"
						:weight="isCommitted ? 'priimary' : 'normal'"
						:disabled="isLoading"
						@click="$emit( 'repreview' )"
					>
						<refresh class="icon-small" />
						{{ isCommitted ? $t( 'Aggregate rerun update' ) : $t( 'Aggregate Rerun' ) }}
					</cdx-button>
				</div>
			</template>
		</cdx-card>
	</div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { CdxCard, CdxButton } from '@wikimedia/codex'
import Check from 'vue-material-design-icons/Check.vue'
import Refresh from 'vue-material-design-icons/Refresh.vue'

const { t: $t } = useI18n()

const props = defineProps( {
	result: {
		type: Object,
		required: true
	},
	isLoading: {
		type: Boolean,
		default: false
	},
	isCommitted: {
		type: Boolean, 
		default: false
	}
} )

defineEmits( [ 'commit', 'repreview' ] )

const pageSize = 25
const currentPage = ref( 1 )

const totalPages = computed( () => {
	return Math.ceil( ( props.result.ranked || [] ).length / pageSize )
} )

const paginatedResults = computed( () => {
	const start = ( currentPage.value - 1 ) * pageSize
	return ( props.result.ranked || [] ).slice(
		start,
		start + pageSize
	)
} )

const pageStart = computed( () => {
	return ( currentPage.value - 1 ) * pageSize + 1
} )

const pageEnd = computed( () => {
	return Math.min(
		currentPage.value * pageSize,
		props.result.ranked?.length || 0
	)
} )

watch(
	() => props.result,
	() => {
		currentPage.value = 1
	}
)

const tiedScores = computed( () => {
	const counts = {}

	for ( const item of props.result.ranked || [] ) {
		counts[ item.score ] = ( counts[ item.score ] || 0 ) + 1
	}

	return new Set(
		Object.keys( counts )
			.filter( ( score ) => counts[ score ] > 1 )
			.map( Number )
	)
} )

function isTied( item ) {
	return tiedScores.value.has( item.score )
}

function runCommit() {
  isLoading.value = true
  adminService
    .commitAggregate(props.campaignId, buildPayload())
    .then((resp) => {
      alertService.success($t('montage-aggregate-committed'))
      committedResult.value = resp.data  // ← mark as committed
      emit('committed')
    })
    .catch(alertService.error)
    .finally(() => {
      isLoading.value = false
    })
}

</script>

<style scoped>
.aggregate-preview {
	width: 100%;
}

.preview-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin-bottom: 16px;
}

.preview-meta {
	display: flex;
	gap: 16px;
	font-size: 0.9em;
	color: var( --color-subtle, #555 );
    margin-right: 40px;
}

.excluded {
	color: #c00;
}

.results-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;
}

.result-card {
	border: 1px solid #dcdcdc;
	border-radius: 8px;
	background: #fff;
	overflow: hidden;
	transition: box-shadow 0.2s ease;
}

.result-card:hover {
	box-shadow: 0 2px 8px rgba( 0, 0, 0, 0.12 );
}

.tied-card {
	background: #fffbe6;
	border-color: #fc3;
}

.image-wrapper {
	width: 100%;
	height: 180px;
	background: #f8f8f8;
	display: flex;
	align-items: center;
	justify-content: center;
}

.image-wrapper img {
	width: 100%;
	height: 100%;
	object-fit: cover;
}

.card-content {
	padding: 12px;
}

.card-rank {
	font-weight: 600;
	margin-bottom: 8px;
}

.image-link {
	display: block;
	margin-bottom: 10px;
	color: #36c;
	text-decoration: none;
	word-break: break-word;
}

.image-link:hover {
	text-decoration: underline;
}

.score {
	font-family: monospace;
	font-size: 0.9rem;
}

.tie-badge {
	display: inline-block;
	margin-left: 6px;
	padding: 2px 6px;
	font-size: 0.75em;
	background: #fc3;
	border-radius: 4px;
	font-weight: 600;
}

.empty-state {
	padding: 32px;
	text-align: center;
	color: #555;
}

.pagination {
	display: flex;
	justify-content: space-between;
	align-items: center;
	margin-top: 24px;
	margin-bottom: 16px;
}

.pagination-info {
	font-size: 0.9rem;
	color: var( --color-subtle, #555 );
}

.pagination-controls {
	display: flex;
	align-items: center;
	gap: 12px;
}

.page-number {
	font-weight: 600;
	min-width: 100px;
	text-align: center;
}

.button-group {
	display: flex;
	gap: 12px;
	justify-content: flex-end;
	margin-top: 24px;
	margin-bottom: 12px;
}

.icon-small {
	font-size: 6px;
}
</style>