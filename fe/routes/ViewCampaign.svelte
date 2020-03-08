<MontageAPI api='/v1/admin/campaign/{params.id}' let:data={data}>
  <h1>{data.name}</h1>
  {JSON.stringify(data)}
</MontageAPI>

<script>
  import MontageAPI from '../MontageAPI.svelte'

  export let params = {}
</script>
