<MontageAPI api='/v1/admin/campaign/{params.id}' let:data={data}>
  <div class="container">
    <p><a href='#'>Admin</a> > {data.name}</p>
  </div>

  <CampaignHead {...data} />

  <div class="container">
    <Paper>
      <Content>
        <Title>Rounds</Title>
        {#each data.rounds as round, i}
          {#if round.status != 'cancelled'}
          <div class="round-row">
            <div class="round-icon" class:active="{round.status === 'active'}">
              <Icon class="material-icons">
                {#if round.vote_method == 'yesno'}
                  thumbs_up_down
                {:else if round.vote_method == 'rating'}
                  star_border
                {:else if round.vote_method == 'ranking'}
                  sort
                {/if}
              </Icon>
            </div>
            {#if round.status != 'active'}
              <span class="round-line"></span>
            {/if}
            <div flex class="round-card">
              <h2 class="mdc-typography--headline6" style="margin: 0;"><a href="#/round/{round.id}">{round.name}</a></h2>
              <h3 class="mdc-typography--subtitle2" style="margin: 0 0 10px; color: #888;">{round.open_date}</h3>
              <div class="round-card-body mdc-typography--body2">
               
              </div>
            </div>
          </div>
          {/if}

          {#if data.rounds.length - 1 === i && round.status != 'active'}
          <div class="round-row">
            <div class="round-icon active">
               <Icon class="material-icons">
                add
              </Icon>
            </div>
            <div flex class="round-card">
              <Button>Next round</Button>
            </div>
          </div>
          {/if}
        {/each}
      </Content>
    </Paper>
  </div>
</MontageAPI>

<style>
  .round-container {
    margin: 0 2em;
  }

  .round-row {
    position: relative;
    flex-direction: row;
    display: flex;
  }

  .round-icon {
    display: flex;
    background-color: #ccc;
    color: #fff;
    width: 40px;
    height: 40px;
    margin-top: 0;
    border-radius: 20px;
    align-items: center;
    align-content: center;
    justify-content: center;
  }

  .active {
    background-color: rgb(51, 102, 204);
  }

  .round-line {
    height: calc(100% - 56px);
    border-left: 1px solid #d6d6d6;
    position: absolute;
    display: block;
    top: 48px;
    left: 20px;
  }

  .round-card {
    flex: 1;
    border-radius: 10px;
    margin-left: 1em;
  }

  .round-card h2 {
    color: rgb(51, 102, 204);
  }

  .round-card h4 {
    margin: 0.2rem 0;
    font-size: 1rem;
    line-height: 1rem;
    font-weight: bold;

  }

  .round-card-body {
    margin: 1em 0;
    padding: 1em;
    background: #fafafa;
  }



</style>

<script>
  import { slide } from 'svelte/transition';
  import Paper, {Title, Subtitle, Content} from '@smui/paper';
  import Chip, {Set, Icon, Text} from '@smui/chips';
  import Card, {Content as CardContent, Media} from '@smui/card';
  import Button from '@smui/button';

  import MontageAPI from '../MontageAPI.svelte'
  import CampaignHead from '../CampaignHead.svelte'

  export let params = {}

</script>
