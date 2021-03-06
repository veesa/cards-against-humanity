#!/usr/bin/python
# -*- coding: utf-8 -*-

import os.path
import sqlite3

from cardlist import CardListWindow
from const import *
from current_card import CurrCardWindow
from shared.card import CARD_BLACK, CARD_WHITE
from shared.configurator import Configurator
from shared.path import getScriptDirectory
from shared.translator import Translator

MENU_NEW_CARD = wx.NewId()
MENU_APPLY_CHANGES = wx.NewId()
MENU_SAVE_ALL = wx.NewId()
MENU_UNDO_ALL = wx.NewId()
MENU_EXIT = wx.NewId()



class MainFrame(wx.Frame):
  def __init__(self):
    wx.Frame.__init__(self, parent=None, title="Card Editor",
                      size=(WIDTH, HEIGHT))
    
    self.config = Configurator('editor')
    self.database = None
    self.translator = Translator('editor')
    self.translator.setLanguage(self.config.get('language'))
    self.unsaved_changes = False
    
    self.SetBackgroundColour("white")
    
    # add menubar
    self.initUI()
    self.Center()
    self.SetMinSize((1067, 463))
    
    # create a splitter and the teo sub-windows
    self.splitter = wx.SplitterWindow(self,
                                 style=wx.SP_LIVE_UPDATE | wx.SP_NO_XP_THEME
                                       | wx.SP_3D,
                                 name="vertical splitter")
    self.splitter.SetBackgroundColour("white")
    self.left_window = CardListWindow(self.splitter)
    self.right_window = CurrCardWindow(self.splitter)
    
    #self.splitter.SetMinimumPaneSize((WIDTH / 5))  # just to prevent moving sash to
    #   the very right or left and so
    #   you can't move it back
    self.splitter.SetSashGravity(0.5)
    # split the frame
    self.splitter.SplitVertically(self.left_window, self.right_window,
                             (0.7 * WIDTH)
                                   )
    
    
    
    # listen to changing sash
    self.splitter.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGING, self.onSashChanging)
    
    self.Bind(wx.EVT_SIZE, self.onResizing)
    
    # calling the database loading algorithm directly after the window appears
    wx.CallAfter(self.initDatabase)
  
  
  def onResizing(self, e):
    e.Skip()
    wx.CallAfter(self.left_window.card_grid.calcBestColumns)
    wx.CallAfter(self.left_window.Layout)
    
  
  def initUI(self):
    menubar = wx.MenuBar()
    file_menu = wx.Menu()
    menu_item = wx.MenuItem(file_menu, MENU_NEW_CARD, self.translator.translate("&New card\tCtrl+N"))
    file_menu.AppendItem(menu_item)
    
    menu_item = wx.MenuItem(file_menu, MENU_APPLY_CHANGES,
                            self.translator.translate("Apply &changes\tCtrl+C"))
    file_menu.AppendItem(menu_item)
    
    menu_item = wx.MenuItem(file_menu, MENU_SAVE_ALL, self.translator.translate("&Save all\tCtrl+S"))
    file_menu.AppendItem(menu_item)
    
    menu_item = wx.MenuItem(file_menu, MENU_UNDO_ALL, self.translator.translate("&Undo all\tCtrl+U"))
    file_menu.AppendItem(menu_item)
    
    menu_item = wx.MenuItem(file_menu, MENU_EXIT,
                            self.translator.translate("&Quit\tCtrl+Q"))  # an underlined and linked Q (Ctrl
    #   + Q also quits)
    file_menu.AppendItem(menu_item)
    
    file_menu.Bind(wx.EVT_MENU, self.onNewCard, id=MENU_NEW_CARD)
    file_menu.Bind(wx.EVT_MENU, self.onApplyChanges, id=MENU_APPLY_CHANGES)
    file_menu.Bind(wx.EVT_MENU, self.onSaveAll, id=MENU_SAVE_ALL)
    file_menu.Bind(wx.EVT_MENU, self.onUndoAll, id=MENU_UNDO_ALL)
    file_menu.Bind(wx.EVT_MENU, self.onQuit, id=MENU_EXIT)
    self.Bind(wx.EVT_CLOSE, self.closeIntervention)
    
    menubar.Append(file_menu, self.translator.translate("&File"))

    language_menu = wx.Menu()

    languages = self.translator.getAvailableLanguages()

    for language in languages:
      id = wx.NewId()
      menu_item = wx.MenuItem(language_menu, id=id, text=language)
      menu_item.SetCheckable(True)
      language_menu.AppendItem(menu_item)
      language_menu.Bind(wx.EVT_MENU, self.onLanguageChange, id=id)

      if language == self.translator.getLanguage():
        menu_item.Check(True)

    menubar.Append(language_menu, self.translator.translate("&Language"))

    self.SetMenuBar(menubar)
  
  
  def initDatabase(self):
    # if no database exists, we will ask to create a new one
    if not os.path.exists(os.path.join(getScriptDirectory(), 'cards.db')):
      result = self.Message(caption="No database found",
                            text="We couldn't find a cards.db file inside the "
                                 "editor's working directory. Do you want us "
                                 "to create a new one for you which you can "
                                 "edit directly afterwards?\nIf no, "
                                 "the editor will close immediately.",
                            style=MSG_YES_NO)
      if result == wx.ID_NO:
        self.Close()
      else:
        self.database = sqlite3.connect(
          os.path.join(getScriptDirectory(), 'cards.db'))
        cursor = self.database.cursor()
        cursor.execute("""
                       CREATE TABLE 'cards' (
                         'id' INTEGER PRIMARY KEY NOT NULL,
                         'text' VARCHAR(1000),
                         'type' TINYINT(1))
                       """)
        self.database.commit()
    else:
      self.database = sqlite3.connect(
        os.path.join(getScriptDirectory(), 'cards.db'))
    
    self.loadCards()
  
  
  # parses the database and fills the grid with cards
  # focus parameter defines if the focus should be set onto the first loaded
  # card at the end of the load automatically
  def loadCards(self, focus=True):
    
    # we need to construct the sql command here
    sql = 'SELECT id, text, type FROM cards'
    
    filter_cmd = []
    filter_prm = []
    
    if self.left_window.toolbar.checkbox_black.GetValue():
      filter_cmd.append('type = ?')
      filter_prm.append(CARD_BLACK)
    
    if self.left_window.toolbar.checkbox_white.GetValue():
      filter_cmd.append('type = ?')
      filter_prm.append(CARD_WHITE)
    
    if len(filter_cmd) > 0:
      sql += ' WHERE (' + ' OR '.join(filter_cmd) + ")"
    
    if self.left_window.toolbar.search_ctrl.GetValue() != '':
      if len(filter_cmd) == 0:
        sql += ' WHERE '
      else:
        sql += ' AND '
      sql += 'text LIKE ?'
      filter_prm.append(
        '%' + self.left_window.toolbar.search_ctrl.GetValue() + '%')
    
    panel = None
    cursor = self.database.cursor()
    cursor.execute(sql, tuple(filter_prm))
    self.left_window.card_grid.Hide()
    self.left_window.card_grid.clearCards()
    for card in cursor.fetchall():
      new_card = self.left_window.card_grid.addCard(card[0], card[1], card[2])
      if panel is None:
        panel = new_card

    if self.left_window.card_grid.initialized is False:
      self.left_window.card_grid.createGrid()
    else:
      self.left_window.card_grid.calcBestColumns(self.ClientSize.height)
      self.left_window.card_grid.Layout()

    self.left_window.toolbar.updateCardCounter()
    self.left_window.card_grid.Show()
    self.left_window.Layout()
    
    if panel is not None and focus:
      panel.SetFocus()
  
  
  def Message(self, caption, text, style):
    message = wx.MessageDialog(parent=self, caption=self.translator.translate(caption), message=self.translator.translate(text),
                               style=style)
    result = message.ShowModal()
    message.Destroy()
    return result
  
  
  # will retrieve a menu item from any menu you want
  def getMenuItem(self, menu, item):
    
    for m in self.MenuBar.GetMenus():
      if m[1] == menu:
        for i in m[0].GetMenuItems():
          if i.Text == item:
            return i
    
    return None
  
  
  def onQuit(self, e):
    self.Close()
  
  
  def closeIntervention(self, e):
    
    if not e.CanVeto():
      self.Destroy()
      return
    
    if not self.right_window.saved:
      result = self.Message(caption="Unapplied changes",
                            text="Your edit window contains unapplied "
                                 "changes. Do you want to apply them now?",
                            style=MSG_YES_NO)
      
      if result == wx.ID_YES and self.right_window.SaveCard(None) == False:
        e.Veto(True)
        return
      elif result == wx.ID_NO:
        if self.right_window.related_card.getCardText() == '':
          self.database.cursor().execute('DELETE FROM cards WHERE id = ?',
                                         (self.right_window.related_card.id,))
          self.left_window.card_grid.deleteCard(self.right_window.related_card)
          self.left_window.toolbar.updateCardCounter()

        self.right_window.Disable()
    
    if self.unsaved_changes:
      result = self.Message(caption="Unsaved changes",
                            text="You changed some cards without saving. Do "
                                 "you want us to save for you?",
                            style=MSG_YES_NO)
      
      if result == wx.ID_YES:
        self.left_window.toolbar.onSaveAll(None)

    self.Destroy()
    self.translator.close()
    self.config.save()
    
    e.Veto(False)
  
  
  def onSashChanging(self, e):
    self.left_window.card_grid.calcBestColumns(self.ClientSize.height)
    
  
  def onNewCard(self, e):

    self.left_window.toolbar.onNewCard(None)
  
  
  def onApplyChanges(self, e):
    self.right_window.SaveCard(None)
  
  
  def onSaveAll(self, e):
    self.left_window.toolbar.onSaveAll(None)
  
  
  def onUndoAll(self, e):
    self.left_window.toolbar.onUndoAll(None)


  def onLanguageChange(self, e):

    item = e.GetEventObject().FindItemById(e.Id)

    if item.Label == self.translator.getLanguage():
      # trying to select the language which is already selected
      item.Check(True)
      return

    self.config.set('language', item.Label)

    self.Message(caption="Change language", text="The language will change after restarting the editor.", style=MSG_INFO)

    for i in e.GetEventObject().GetMenuItems():
      i.Enable(False)
      i.Check(False)

    item.Check(True)


def onEraseBackGround(e):
  # do nothing
  # for flicker-fix
  pass



def main():
  app = wx.App(False)
  frame = MainFrame()
  frame.Show()
  app.MainLoop()
