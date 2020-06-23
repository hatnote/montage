<TopAppBar variant="static" {dense}>
  <div class="top-bar-container">
    <Row>
      <Section>
        <IconButton>
          <a href="#/"><img src="../dist/images/logo_white_fat.svg" alt="montage"></a>
        </IconButton>
        <Title>Montage Admin</Title>
      </Section>
      <Section align="end" toolbar>
        <div use:GroupItem>
          <Button color="secondary" on:click={() => menu.setOpen(true)}>
            <Icon class="material-icons" aria-label="Slaporte">person</Icon>
            <Label>Slaporte</Label>
          </Button>
          <Menu bind:this={menu} anchorCorner="BOTTOM_LEFT">
            <List>
                <Item><Text>Settings</Text></Item>
                <Item><Text>Log out</Text></Item>
            </List>
          </Menu>
        </div>
      </Section>
    </Row>
  </div>
</TopAppBar>

<Router {routes}/>

<script>
  import TopAppBar, {Section, Title, Row} from '@smui/top-app-bar';
  import IconButton from '@smui/icon-button';
  import Button, {Icon, Label, GroupItem} from '@smui/button';
  import Menu from '@smui/menu';
  import List, {Item, Separator, Text} from '@smui/list';

  import Router from 'svelte-spa-router'

  import Campaigns from './routes/Campaigns.svelte'
  import NewCampaign from './routes/NewCampaign.svelte'
  import ViewCampaign from './routes/ViewCampaign.svelte'
  import EditCampaign from './routes/EditCampaign.svelte'
  import ViewRound from './routes/ViewRound.svelte'

  let dense = true;
  let menu;

  const routes = {
    // Exact path
    '/': Campaigns,
    '/new-campaign': NewCampaign,
    '/campaign/:id': ViewCampaign,
    '/campaign/:id/edit': EditCampaign,
    '/round/:id': ViewRound,

    // Catch-all
    // This is optional, but if present it must be the last
    //'*': NotFound,
  }
</script>

<style>
  .top-bar-container {
    width: 800px;
    margin: 0 auto;
  }

  :global(.full-width-table) {
    width: 100%;
  }
</style>
