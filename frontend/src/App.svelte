<script>
  import Router from "svelte-spa-router";
  import Header from "./components/Header.svelte";
  import Toast from "./components/Toast.svelte";
  import Home from "./pages/Home.svelte";
  import Dashboard from "./pages/Dashboard.svelte";
  import MeetingDetail from "./pages/MeetingDetail.svelte";
  import Chat from "./pages/Chat.svelte";
  import ActionItems from "./pages/ActionItems.svelte";
  import Search from "./pages/Search.svelte";
  import "./app.css";

  const routes = {
    "/": Home,
    "/meetings": Dashboard,
    "/meetings/:id": MeetingDetail,
    "/chat": Chat,
    "/actions": ActionItems,
    "/search": Search,
  };
</script>

<div class="min-h-screen bg-surface-50">
  <Header />
  <main>
    <Router {routes} />
  </main>
  <Toast />
</div>
