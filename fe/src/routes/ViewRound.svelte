<MontageAPI api='/v1/admin/round/{params.id}' let:data={data}>

  <div class="container">
    <p><a href='#'>Admin</a> > <a href='#/campaign/{data.campaign.id}'>{data.campaign.name}</a> > {data.name}</p>
  </div>

  <CampaignHead {...data.campaign} round_name={data.name}/>

  <div class="container">
    <Paper>
      <Content>
        <Title>{data.name}</Title>
        
        <p>Status: {data.status}</p>
        <p>Vote method: {data.vote_method}</p>

        <h2>Voting Deadline</h2>
        {data.deadline_date}
        
        <h2>Directions</h2>
        {data.directions}

        <h2>Quorum</h2>
        <p>The quorum is the number of jurors that will see each entry.</p>
        {data.quorum}

        <h2>Round stats</h2>
        <ul>
          <li>all_mimes: {data.stats.all_mimes}</li>
          <li>percent_tasks_open:  {data.stats.percent_tasks_open}</li>
          <li>total_cancelled_tasks: {data.stats.total_cancelled_tasks}</li>
          <li>total_disqualified_entries:  {data.stats.total_disqualified_entries}</li>
          <li>total_open_tasks: {data.stats.total_open_tasks}</li>
          <li>total_round_entries: {data.stats.total_round_entries}</li>
          <li>total_tasks: {data.stats.total_tasks}</li>
          <li>total_uploaders: {data.stats.total_uploaders}</li>
        </ul>
          
        
        <h2>Voting stats</h2>
        <DataTable class="full-width-table">
          <Head>
            <Row>
              <Cell>Username</Cell>
              <Cell>Active</Cell>
              <Cell>Percent open tasks</Cell>
              <Cell>Total tasks</Cell>
            </Row>
          </Head>
          <Body>
          {#each data.jurors as juror}
            <Row>
              <Cell>{juror.username}</Cell>
              <Cell>{juror.is_active}</Cell>
              <Cell>{juror.stats.percent_tasks_open}</Cell>
              <Cell>{juror.stats.total_tasks}</Cell>
            </Row>
          {/each}
          </Body>
        </DataTable>

      </Content>
    </Paper>
  </div>
</MontageAPI>

<script>
  import Paper, {Title, Subtitle, Content} from '@smui/paper';
  import DataTable, {Head, Body, Row, Cell} from '@smui/data-table';
  import MontageAPI from '../MontageAPI.svelte'
  import CampaignHead from '../CampaignHead.svelte'

  export let params = {}

</script>
