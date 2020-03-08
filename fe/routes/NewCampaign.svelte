<Paper>
  <Title>Create a new campaign</Title>
  <Content>
    <h2>Basic information</h2>
    <Textfield
      fullwidth
      value=""
      label="Name"
      input$aria-controls="helper-text"
      input$aria-describedby="helper-text" />
    <HelperText id="helper-text">Campaign name</HelperText>

    <Textfield
      fullwidth
      value=""
      label="Campaign URL"
      input$aria-controls="helper-text"
      input$aria-describedby="helper-text" />
    <HelperText id="helper-text">URL for your campaign website</HelperText>

    <div>
      <h2>Date range</h2>
      <p>Select the start and end date for the competition you will be judging. When you import photos, you can disqualify photos that were not uploaded during this range.</p>
      <Textfield value="" label="Start date" type="date" />
      <Textfield value="" label="End date" type="date" />
    </div>
    <h2>Coordinators</h2>
    <p>Coordinators are people who have access to editing the campaign and rounds, and viewing voting statistics.</p>


    <Set bind:chips={coordinators} chips={coordinators} let:chip input>
      <Chip><Text>{chip}</Text><Icon class="material-icons" trailing tabindex="0">cancel</Icon></Chip>
    </Set>


    <Textfield
      bind:value={search_name}
      on:keyup={({ target: { value } }) => debounce(search_name)}
      label="Name"
      input$aria-controls="helper-text"
      input$aria-describedby="helper-text" />

      {#await confirmed_username}
      Confirming...
      {:then confirmed_username}
         {#if search_name != '' && confirmed_username}
          <Button on:click={addName}><Label>Add</Label></Button>
        {:else}
          <Button disabled><Label>Add</Label> </Button>
        {/if}
      {/await}

  </Content>
</Paper>



<script>
  import Textfield, {Input, Textarea} from '@smui/textfield';
  import Paper, {Title, Subtitle, Content} from '@smui/paper';
  import HelperText from '@smui/textfield/helper-text/index';
  import Button, {Label} from '@smui/button';
  import Chip, {Set, Icon, Checkmark, Text} from '@smui/chips';


  let confirmed_username;
  let chipSet;
  let search_name = '';
  let coordinators = ['test'];






  function addName() {
    coordinators = [...coordinators, search_name];
    console.log(coordinators)
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