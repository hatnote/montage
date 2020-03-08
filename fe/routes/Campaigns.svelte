<h1>Campaigns</h1>

<div class="controls">
  <a href="#/new-campaign">
  <Button variant=raised>
    <Icon class="material-icons">add</Icon>
    <Label>New campaign</Label>
  </Button>
  </a>
</div>

<h2>Wiki Loves Monuments</h2>
  <MontageAPI api='/v1/admin' let:data={data}>
    <DataTable class="full-width-table">
      <Head>
        <Row>
          <Cell>Name</Cell>
          <Cell>Open date</Cell>
          <Cell>Close date</Cell>
        </Row>
      </Head>
      <Body>
      {#each data as campaign}
        <Row>
          <Cell><a href="#/campaign/{campaign.id}">{campaign.name}</a></Cell>
          <Cell>{campaign.open_date.split('T')[0]}</Cell>
          <Cell>{campaign.close_date.split('T')[0]}</Cell>
        </Row> 
      {/each}
      </Body>
    </DataTable>
  </MontageAPI>

<style>
.controls {
    margin-bottom: 1em;
  }
</style>

<script>
  import Button, {Label, Icon} from '@smui/button';
  import DataTable, {Head, Body, Row, Cell} from '@smui/data-table';
  import MontageAPI from '../MontageAPI.svelte'
</script>
