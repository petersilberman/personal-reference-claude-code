# Tasks Dashboard

> [!warning]- Needs Attention
>
> ### Overdue
>
> ```tasks
> not done
> due before today
> sort by due
> ```
>
> ### Due This Week
>
> ```tasks
> not done
> due after yesterday
> due before in 7 days
> sort by due
> ```
>
> ### In Progress
>
> ```tasks
> status.type is IN_PROGRESS
> ```
>
> ### Waiting
>
> ```tasks
> not done
> description includes #waiting
> ```

---

## All Open Tasks (non-1-1)

```tasks
not done
path does not include journal/1-1s
path does not include journal/weekly
path does not include tmp/
path does not include node_modules/
path does not include capture/google-tasks
path does not include projects/
path does not include learning/
path does not include assets/
path regex does not match /^TASKS.md$/
```

---

## Include for Status

```tasks
not done
description includes #status
sort by due
```

---

## Staff Meeting

Staff meeting with direct reports.

```tasks
not done
description includes #staff
sort by due
```

---

## Google Tasks

```tasks
not done
path includes capture/google-tasks
(due before in 2 weeks) OR (no due date)
description does not include #status
description does not include #staff
description does not include #alice
sort by due
```

---

## Overview By Person

### Alice (Product Lead)

```tasks
not done
(path includes journal/1-1s/product-lead) OR (description includes #alice)
sort by due
```
