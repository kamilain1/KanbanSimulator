import json

from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from .models import Room, Team, Day, Player, Card, Character, UserStory
from .forms import CreateRoomForm, JoinRoomForm, PlayerFormSet
import random

NUMBER_OF_CHARACTERS = 7
CARDS_IN_GAME = 10


def index(request):
    if request.method == 'POST':
        form = CreateRoomForm(request.POST)
        if form.is_valid():
            # creating the room
            new_room = Room()
            new_room.save()

            # getting data from the form
            player_name = form.cleaned_data['name']
            spectator = form.cleaned_data['spectator']
            teams_num = form.cleaned_data['teams_num']

            # creating teams
            for i in range(teams_num):
                new_team = Team(name='Команда ' + str(i), game=new_room)
                new_team.save()

            # creating player
            new_player = Player(name=player_name, team=new_room.team_set.first(), spectator=spectator,
                                creator=True)
            new_player.save()
            return HttpResponseRedirect(reverse('board:waitingRoom', args=(new_player.pk,)))
    else:
        form = CreateRoomForm()
        return render(request, 'board/index.html', {'form': form})


@csrf_exempt
def board(request, player_id):
    player = Player.objects.get(pk=player_id)
    return render(request, 'board/board.html', {'player': player})


# temporary function for testing (board clearing and etc.)
def initial_conditions(team_id):
    team = Team.objects.get(pk=team_id)
    Card.objects.filter(team=team).update(column_number=0, row_number=0, analytic_completed=0,
                                          develop_completed=0, test_completed=0, ready_day=-1, age=0)

    Character.objects.filter(team=team).delete()
    for i in range(7):
        character = Character(team=team, role=i)
        character.save()

    team.version = 0
    team.dayNum = 0
    team.save()


# initial backlog population function
@csrf_exempt
def populateBackLog(request):
    if request.method == 'POST':
        # request_room = request.POST.get('room', 0)
        request_team = request.POST.get('team', 0)

        # testing purposes
        initial_conditions(request_team)

        cards = Card.objects.filter(team=request_team).values('pk', 'title', 'age', 'is_expedite', 'ready_day',
                                                              'analytic_remaining', 'analytic_completed',
                                                              'develop_remaining', 'develop_completed',
                                                              'test_remaining', 'test_completed',
                                                              'column_number', 'row_number')

        team = Team.objects.get(pk=request_team)

        # Team start day and wip limits (don't forget to change it later)
        team.dayNum = 1
        team.wip_limit1 = 4
        team.wip_limit2 = 4
        team.wip_limit3 = 4
        team.save()

        board_info = {"Age": team.dayNum,
                      "Wip1": team.wip_limit1,
                      "Wip2": team.wip_limit2,
                      "Wip3": team.wip_limit3}

        return JsonResponse(
            {"cards": json.dumps(list(cards)), "board_info": json.dumps(board_info),
             "team_effort": json.dumps(generate_random_effort_for_whole_team())},
            status=200)

    return JsonResponse({"error": ""}, status=400)


# .. in process
@csrf_exempt
def start_new_day(request):
    if request.method == 'POST':
        day_num = request.POST.get('current_day', 0)
        team_num = request.POST.get('team', 0)
        team = Team.objects.get(pk=team_num)
        if int(day_num) == int(team.dayNum):
            cards = json.loads(request.POST.get('cards', []))
            characters = request.POST.getlist("characters[]", [])
            anl_comp = request.POST.get('anl_completed', 0)
            dev_comp = request.POST.get('dev_completed', 0)
            test_comp = request.POST.get('test_completed', 0)

            for card in cards:
                print("Column_number", card["column_number"])
                Card.objects.filter(pk=card["pk"]).update(age=card["age"], ready_day=card["ready_day"],
                                                          analytic_completed=card["analytic_completed"],
                                                          develop_completed=card["develop_completed"],
                                                          test_completed=card["test_completed"],
                                                          row_number=card["row_number"],
                                                          column_number=card["column_number"])
            for i in range(len(characters)):
                Character.objects.filter(team=team, role=i).update(card_id=characters[i])

            day = Day(age=int(day_num) + 1, team=team, anl_completed_tasks=anl_comp, dev_completed_tasks=dev_comp,
                      test_completed_tasks=test_comp)
            day.save()
            team.version += 1
            team.dayNum = int(day_num) + 1
            team.save()
            return JsonResponse({"SYN": True, "day_num": int(day_num) + 1,
                                 "team_effort": json.dumps(generate_random_effort_for_whole_team())}, status=200)

        return JsonResponse({"SYN": False}, status=200)


# function which generates random efforts for the characters
def generate_random_effort_for_whole_team():
    team_effort = []
    for i in range(NUMBER_OF_CHARACTERS):
        team_effort.append(random.randint(1, 6))
    return team_effort


# accepts actual position of the character and updates it in the db
@csrf_exempt
def move_card(request):
    if request.method == "POST":
        team = request.POST.get('team_id', -1)
        id = request.POST.get('id', -1)
        col = request.POST.get('col_num', -1)
        row = request.POST.get('row_num', -1)

        if team != - 1 and id != -1 and col != -1 and row != -1:
            Card.objects.filter(pk=id).update(column_number=col, row_number=row)
            old_version = Team.objects.get(pk=team).version
            Team.objects.filter(pk=team).update(version=old_version + 1)
            print("Card#", id, " was moved on column#", col, "row#", row)

    return JsonResponse({"Success": ""}, status=200)


# accepts actual position of the character and updates it in the db
@csrf_exempt
def move_player(request):
    if request.method == "POST":
        team_id = request.POST.get('team_id', -1)
        card_id = request.POST.get('card_id', -1)
        role = request.POST.get('role')

        if team_id != -1 and role != -1:
            team = Team.objects.get(pk=team_id)
            Character.objects.filter(team=team, role=role).update(card_id=card_id)
            team.version += 1
            team.save()
            print("Character was moved on card#", card_id)

    return JsonResponse({"Success": ""}, status=200)


# check board version
@csrf_exempt
def version_check(request):
    if request.method == "POST":
        input_version = request.POST.get('version', -1)
        input_team = request.POST.get('team_id', -1)
        server_team = Team.objects.get(pk=input_team)
        if int(server_team.version) > int(input_version):
            cards = Card.objects.filter(team=server_team).values('pk', 'title', 'age', 'is_expedite', 'ready_day',
                                                                 'analytic_remaining', 'analytic_completed',
                                                                 'develop_remaining', 'develop_completed',
                                                                 'test_remaining', 'test_completed',
                                                                 'column_number', 'row_number')
            characters = Character.objects.filter(team=server_team).values('role', 'card_id')
            board_info = {"version": server_team.version,
                          "Age": server_team.dayNum,
                          "Wip1": server_team.wip_limit1,
                          "Wip2": server_team.wip_limit2,
                          "Wip3": server_team.wip_limit3}
            return JsonResponse({"cards": json.dumps(list(cards)),
                                 "characters": json.dumps(list(characters)),
                                 "board_info": json.dumps(board_info), "SYN": False}, status=200)
        else:
            return JsonResponse({"SYN": True}, status=200)

    return JsonResponse({"Error": "error"}, status=400)


@csrf_exempt
def players_check(request, player_id):
    if request.method == "POST":
        game_id = request.POST.get('game_id', -1)
        game = Room.objects.get(pk=game_id)
        input_version = request.POST.get('version')
        server_version = Room.objects.get(pk=game_id).version
        if int(server_version) > int(input_version):
            player_set = []
            teams = Team.objects.filter(game=game)
            counter = 0
            for team in teams:
                players = Player.objects.filter(team=team)
                counter += 1
                for player in players:
                    player_set.append({"name": player.name,
                                       "team_number": counter,
                                       "team_id": team.pk,
                                       "spectator": player.spectator})

            return JsonResponse({"players": json.dumps(list(player_set)),
                                 "version": server_version, "SYN": False}, status=200)
        else:
            return JsonResponse({"SYN": True}, status=200)

    return JsonResponse({"Error": "error"}, status=400)


def join_room(request, room_id):
    if request.method == 'POST':
        form = JoinRoomForm(request.POST)
        if form.is_valid():
            # getting data from the form
            player_name = form.cleaned_data['name']
            spectator = form.cleaned_data['spectator']

            # get room to join
            room = Room.objects.get(pk=room_id)

            # selecting team to join
            selected_team = room.team_set.first()
            min_players_num = len(selected_team.player_set.filter(spectator=False))
            for team in room.team_set.all():
                if len(team.player_set.filter(spectator=False)) < min_players_num:
                    selected_team = team
                    min_players_num = len(selected_team.player_set.filter(spectator=False))

            # creating player
            new_player = Player(name=player_name, team=selected_team,
                                spectator=spectator,
                                creator=False)
            new_player.save()

            # incrementing room version
            room.version += 1
            room.save()

            return HttpResponseRedirect(reverse('board:waitingRoom', args=(new_player.pk,)))
    else:
        form = JoinRoomForm()

    return render(request, 'board/join_room.html', {'form': form})


def waiting_room(request, player_id):
    player = Player.objects.get(pk=player_id)
    game_id = player.team.game.pk
    return render(request, 'board/waiting_room.html', {'player': player, 'game': game_id})


def manage_players(request, player_id):
    if request.method == 'POST':
        formset = PlayerFormSet(request.POST)
        if formset.is_valid():
            formset.save()
        return HttpResponseRedirect(reverse('board:startGame', args=(player_id,)))
    else:
        room = Player.objects.get(pk=player_id).team.game
        players = Player.objects.filter(team_id__in=room.team_set.values('pk')).order_by('team_id')
        formset = PlayerFormSet(queryset=players)
        choices = room.team_set.all()
        return render(request, 'board/manage_players.html', {'formset': formset, 'choices': choices})


def start_game(request, player_id):
    room = Player.objects.get(pk=player_id).team.game
    team_set = room.team_set.all()

    # creating cards
    # cards that will be actually used in the game
    cards_set = []

    # getting random set of cards
    chosen_indexes = set()
    user_stories = UserStory.objects.filter(is_expedite=False)

    for i in range(CARDS_IN_GAME):
        number_found = False
        while not number_found:
            j = random.randint(0, len(user_stories) - 1)
            if j in chosen_indexes:
                continue

            cards_set.append(user_stories[j])
            chosen_indexes.add(j)
            number_found = True

    for team in team_set:
        # creating cards for each team
        row = 0
        for card in cards_set:
            new_card = Card(title=card.title, team=team, analytic_remaining=card.analytic_points,
                            develop_remaining=card.develop_points, test_remaining=card.test_points, row_number=row,
                            business_value=card.business_value)
            new_card.save()
            row = row + 1

        # creating characters for each team
        for i in range(7):
            character = Character(team=team, role=i)
            character.save()

    room.ready = True
    room.save()
    return HttpResponseRedirect(reverse('board:board', args=(player_id,)))


def join_game(request, player_id):
    player = Player.objects.get(pk=player_id)
    if player.team.game.ready:
        return HttpResponseRedirect(reverse('board:board', args=(player_id,)))


def rules(request):
    return render(request, 'board/rules.html')


# to be added
def news(request):
    return
