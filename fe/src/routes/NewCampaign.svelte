<Paper>
  <Title>Create a new campaign</Title>
  <Content>
    <h2>Basic information</h2>
    <div>
      <Select enhanced bind:value={series_choice} label="Series">
      <MontageAPI api='/v1/series' let:data={serieses}>
        {#each serieses as series}
          <Option value={series.id}>{series.name}</Option>
        {/each}
        <Option value="new">New Series</Option>
      </MontageAPI>
      </Select>
    </div>

    <Textfield
      fullwidth
      bind:value={name}
      label="Name"
      input$aria-controls="helper-text"
      input$aria-describedby="helper-text" />
    <HelperText id="helper-text">Campaign name</HelperText>

    <Textfield
      fullwidth
      bind:value={url}
      label="Campaign URL"
      input$aria-controls="helper-text"
      input$aria-describedby="helper-text" />
    <HelperText id="helper-text">URL for your campaign website</HelperText>

    <div>
      <h2>Date range</h2>
      <p>Select the start and end date for the competition you will be judging. When you import photos, you can disqualify photos that were not uploaded during this range.</p>
      <Textfield bind:value={startDate} label="Start date" type="date" />
      <Textfield bind:value={endDate} label="End date" type="date" />
    </div>
    <h2>Coordinators</h2>
    <p>Coordinators are people who have access to editing the campaign and rounds, and viewing voting statistics.</p>

    <Textfield
      bind:value={search_name}
      on:keyup={({ target: { value } }) => debounce(search_name)}
      label="Name"/>

      {#await confirmed_username}
      Confirming...
      {:then confirmed_username}
         {#if search_name != '' && confirmed_username}
          <Button on:click={addName}><Label>Add</Label></Button>
        {:else}
          <Button disabled><Label>Add</Label> </Button>
        {/if}
      {/await}

    <Set chips={coordinators} let:chip input>
      <Chip><Text>{chip}</Text><Icon class="material-icons" trailing tabindex="0">cancel</Icon></Chip>
    </Set>
    <h2>Next</h2>
    <p>After you create the campaign, you will create and add photos to the first round.</p>
  </Content>
</Paper>
<div style="display: flex; align-items: center; flex-wrap: wrap;">
  <Button variant="raised" float="right" style="width:100%" on:click|once={addCampaign}>
    <Icon class="material-icons">add</Icon>
    <Label>Create</Label>
  </Button>
</div>

{#if post_promise}
  {#await post_promise}
  ... creating campaign
  {:then post_data}
    Created: {post_data.data.name}
  {/await}
{/if}

<script>
  import Select, {Option} from '@smui/select';
  import Textfield, {Input, Textarea} from '@smui/textfield';
  import Paper, {Title, Subtitle, Content} from '@smui/paper';
  import HelperText from '@smui/textfield/helper-text/index';
  import Button, {Label} from '@smui/button';
  import Chip, {Set, Icon, Text} from '@smui/chips';

  import MontageAPI from '../MontageAPI.svelte'

  let post_promise;

  // post data
  let series;
  let name = '';
  let url = '';
  let startDate = ''; // this should default to september 1 the previous year
  let endDate = ''; // this should probably default to september 30 the previous year
  let coordinators = [];

  async function addCampaign() {
    const api_url = '/v1/admin/add_campaign'
    const settings = {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          'name': name,
          'coordinators': coordinators,
          'open_date': startDate,
          'close_date': endDate,
          'url': url,
          'series_id': series_choice
        })
    }
    const resp = await fetch(api_url, settings)
    const data = await resp.json()
    post_promise = data
    return data
  }


  let confirmed_username;
  let search_name = '';

  let series_choice;

  function addName() {
    if(!coordinators.includes(search_name)) {
      coordinators = [...coordinators, search_name];
    } else {
      console.log('already have it!')
      console.log(coordinators)
    }
  }

  let debounced_name='';
  let timer;

  const debounce = v => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      debounced_name = v;
    }, 350);
  }

  $: {
    confirmed_username = check_username(debounced_name)
  } 

  async function check_username(str) {
    if (!str) {
      return []
    }
    var url = 'https://commons.wikimedia.org/w/api.php'
    var params = {action: 'query',
                  agufrom: str,
                  format: 'json',
                  list: 'globalallusers',
                  rawcontinue: 'true',
                  limit: 1}
    url = url + '?origin=*'
    Object.keys(params).forEach(function(key){
      url += "&" + key + "=" + params[key]
    })
    var response = await fetch(url)
    var json = await response.json()

    return json.query.globalallusers[0].name === str
  }

</script>