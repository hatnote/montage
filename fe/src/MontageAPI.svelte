{#await resp}
    loading...
{:then resp}
    {#if resp.errors.length > 0}
        {resp.errors}
    {:else}
        <slot data={resp.data}></slot>
    {/if}
{/await}

<Dialog
  bind:this={dialog}
  aria-labelledby="dialog-title"
  aria-describedby="dialog-content"
>
  <Title id="dialog-title">{error_title}</Title>
  <Content id="dialog-content">
    {error_body}
  </Content>
  <Actions>
    <Button>
      <Label>Continue</Label>
    </Button>
  </Actions>
</Dialog>

<script>
    import Dialog, {Title, Content, Actions} from '@smui/dialog';
    import Button, {Label} from '@smui/button';

    let dialog;

    let error_title;
    let error_body;

    function deleteItem() {
    // TODO: delete the item.
  }

    export let api;

    async function get_api(montage_api) {
        const resp = await fetch(montage_api);
        if (resp.ok) {
            const json = await resp.json();
            return json
        } else {
            return {'errors': resp.statusText}
        }
    }

    let resp = get_api(api)

    resp.then(resp => {
        if (resp.errors.length > 0) {
            error_title = 'Error'
            error_body = resp.errors
            dialog.open()
        }
    });

</script>
