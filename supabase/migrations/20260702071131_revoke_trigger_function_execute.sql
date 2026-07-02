-- Trigger functions are invoked only by their triggers; client roles must not
-- be able to call them through the /rest/v1/rpc endpoint (security advisor
-- findings 0028/0029 on the SECURITY DEFINER handle_new_user).
revoke execute on function public.handle_new_user() from public, anon, authenticated;
revoke execute on function public.set_updated_at() from public, anon, authenticated;
