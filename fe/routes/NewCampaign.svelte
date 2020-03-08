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

    <Textfield
      bind:value={search_name}
      on:keyup={({ target: { value } }) => debounce(search_name)}
      label="Name"
      input$aria-controls="helper-text"
      input$aria-describedby="helper-text" />

      <Button>
        add
      </Button>

      {#await usernames}
      loading...
      {:then usernames}
      <Menu 
        bind:this={menu}
        anchorCorner="BOTTOM_LEFT">
      
        <List>
          {#each usernames as username}
            <Item><Text>{username}</Text></Item>
          {/each}
        </List>
      </Menu>
      {/await}

  </Content>
</Paper>

<script>
  import Textfield, {Input, Textarea} from '@smui/textfield';
  import Paper, {Title, Subtitle, Content} from '@smui/paper';
  import HelperText from '@smui/textfield/helper-text/index';
  import Menu from '@smui/menu';
  import {Anchor} from '@smui/menu-surface';
  import Button, {Icon, Label, GroupItem} from '@smui/button';
  import List, {Item, Separator, Text} from '@smui/list';

  let usernames;
  let menu;
  let search_name = '';

  let debounced_name='';
  let timer;

  const debounce = v => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      debounced_name = v;
    }, 350);
  }

  $: {
    usernames = get_usernames(debounced_name)
    usernames.then(() => {
      menu.setOpen(true)
    })
  } 

  async function get_usernames(str) {
    if (!str) {
      return []
    }
    var url = 'https://commons.wikimedia.org/w/api.php'
    var params = {action: 'query',
                  agufrom: str,
                  format: 'json',
                  list: 'globalallusers',
                  rawcontinue: 'true'}
    url = url + '?origin=*'
    Object.keys(params).forEach(function(key){
      url += "&" + key + "=" + params[key]
    })
    var response = await fetch(url)
    var json = await response.json()

    var users = json.query.globalallusers.map(user => user.name)
    return users
  }

</script>